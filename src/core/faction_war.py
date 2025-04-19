"""
Faction War System for Veramon Reunited

This module handles the core functionality for faction wars,
including war declaration, battle tracking, territory control,
and reward distribution.
"""

import json
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

from src.db.db import get_connection
from src.utils.config_manager import get_config
from src.core.faction_economy import get_faction_economy

class FactionWar:
    """
    Core faction war system that manages faction vs faction competitions,
    territory control, and associated rewards.
    """
    
    @staticmethod
    async def initialize_database():
        """
        Initialize database tables for faction wars and territories.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Create faction wars table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faction_wars (
                    war_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_faction_id INTEGER NOT NULL,
                    defender_faction_id INTEGER NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status TEXT NOT NULL,
                    attacker_score INTEGER DEFAULT 0,
                    defender_score INTEGER DEFAULT 0,
                    winner_faction_id INTEGER,
                    territory_id INTEGER,
                    FOREIGN KEY (attacker_faction_id) REFERENCES factions(faction_id),
                    FOREIGN KEY (defender_faction_id) REFERENCES factions(faction_id)
                )
            """)
            
            # Create war battles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faction_war_battles (
                    battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    war_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    faction_id INTEGER NOT NULL,
                    opponent_user_id TEXT,
                    opponent_faction_id INTEGER,
                    points_earned INTEGER NOT NULL,
                    battle_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (war_id) REFERENCES faction_wars(war_id),
                    FOREIGN KEY (faction_id) REFERENCES factions(faction_id),
                    FOREIGN KEY (opponent_faction_id) REFERENCES factions(faction_id)
                )
            """)
            
            # Create territories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faction_territories (
                    territory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    controlling_faction_id INTEGER,
                    capture_date TIMESTAMP,
                    defense_value INTEGER DEFAULT 100,
                    daily_token_bonus INTEGER NOT NULL,
                    daily_xp_bonus INTEGER NOT NULL,
                    biome_type TEXT,
                    exclusive_veramon TEXT,
                    FOREIGN KEY (controlling_faction_id) REFERENCES factions(faction_id)
                )
            """)
            
            # Add some default territories if none exist
            cursor.execute("SELECT COUNT(*) FROM faction_territories")
            territory_count = cursor.fetchone()[0]
            
            if territory_count == 0:
                territories = [
                    ("Emerald Forest", "A lush forest territory with abundant plant life.", 100, 50, "forest", "Leafeon,Trevenant"),
                    ("Volcanic Ridge", "A dangerous volcanic area with high temperatures.", 150, 75, "volcanic", "Magmar,Heatran"),
                    ("Crystal Cavern", "An underground cavern filled with beautiful crystals.", 125, 60, "cave", "Carbink,Gigalith"),
                    ("Azure Coast", "A beautiful coastal region with pristine beaches.", 100, 50, "coastal", "Vaporeon,Staryu"),
                    ("Thunder Plains", "A wide open area frequently struck by lightning.", 175, 80, "plains", "Jolteon,Electabuzz"),
                    ("Frozen Tundra", "A frigid wasteland covered in snow and ice.", 150, 70, "tundra", "Glaceon,Beartic"),
                    ("Shadow Woods", "A dark forest shrouded in perpetual night.", 200, 100, "dark_forest", "Umbreon,Darkrai")
                ]
                
                for territory in territories:
                    cursor.execute("""
                        INSERT INTO faction_territories (
                            name, description, daily_token_bonus, daily_xp_bonus, 
                            biome_type, exclusive_veramon
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, territory)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    async def declare_war(attacker_faction_id: int, defender_faction_id: int, territory_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Declare war on another faction.
        
        Args:
            attacker_faction_id: ID of the attacking faction
            defender_faction_id: ID of the defending faction
            territory_id: Optional ID of the territory being fought over
            
        Returns:
            Dict: Result of the war declaration
        """
        # Security checks
        if attacker_faction_id == defender_faction_id:
            return {"success": False, "error": "Cannot declare war on your own faction"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if attacker faction exists
            cursor.execute("SELECT treasury, faction_level, name FROM factions WHERE faction_id = ?", (attacker_faction_id,))
            attacker_data = cursor.fetchone()
            
            if not attacker_data:
                return {"success": False, "error": "Attacker faction does not exist"}
            
            attacker_treasury, attacker_level, attacker_name = attacker_data
            
            # Check if defender faction exists
            cursor.execute("SELECT faction_level, name FROM factions WHERE faction_id = ?", (defender_faction_id,))
            defender_data = cursor.fetchone()
            
            if not defender_data:
                return {"success": False, "error": "Defender faction does not exist"}
            
            defender_level, defender_name = defender_data
            
            # Check if attacker has minimum level to declare war
            min_war_level = get_config("faction", "min_war_level", 5)
            if attacker_level < min_war_level:
                return {
                    "success": False, 
                    "error": f"Your faction must be at least level {min_war_level} to declare war"
                }
            
            # Check if there's already an active war between these factions
            cursor.execute("""
                SELECT war_id FROM faction_wars
                WHERE (attacker_faction_id = ? AND defender_faction_id = ? OR
                       attacker_faction_id = ? AND defender_faction_id = ?)
                AND status = 'active'
            """, (attacker_faction_id, defender_faction_id, defender_faction_id, attacker_faction_id))
            
            if cursor.fetchone():
                return {"success": False, "error": "There is already an active war between these factions"}
            
            # Check if the attacker has reached their war limit
            max_active_wars = get_config("faction", "max_active_wars", 3)
            
            cursor.execute("""
                SELECT COUNT(*) FROM faction_wars
                WHERE (attacker_faction_id = ? OR defender_faction_id = ?)
                AND status = 'active'
            """, (attacker_faction_id, attacker_faction_id))
            
            if cursor.fetchone()[0] >= max_active_wars:
                return {
                    "success": False, 
                    "error": f"Your faction is already involved in the maximum {max_active_wars} wars"
                }
            
            # Check if declaration cooldown has passed
            war_cooldown_days = get_config("faction", "war_cooldown_days", 3)
            
            cursor.execute("""
                SELECT COUNT(*) FROM faction_wars
                WHERE (attacker_faction_id = ? AND defender_faction_id = ? OR
                       attacker_faction_id = ? AND defender_faction_id = ?)
                AND datetime(end_time) > datetime('now', ?)
            """, (attacker_faction_id, defender_faction_id, defender_faction_id, attacker_faction_id, f"-{war_cooldown_days} days"))
            
            if cursor.fetchone()[0] > 0:
                return {
                    "success": False, 
                    "error": f"You must wait {war_cooldown_days} days after the end of a war before declaring a new one"
                }
                
            # Check for level difference protection (prevent high level factions from bullying low levels)
            max_level_difference = get_config("faction", "max_war_level_difference", 5)
            level_difference = abs(attacker_level - defender_level)
            
            if level_difference > max_level_difference:
                return {
                    "success": False, 
                    "error": f"Cannot declare war on factions with more than {max_level_difference} level difference"
                }
            
            # Check if the attacker has the war declaration cost
            declaration_cost = get_config("faction", "war_declaration_cost", 50000)
            
            if attacker_treasury < declaration_cost:
                return {
                    "success": False, 
                    "error": f"Insufficient treasury funds. War declaration costs {declaration_cost:,} tokens"
                }
            
            # If territory_id is provided, check if it exists
            if territory_id:
                cursor.execute("SELECT controlling_faction_id FROM faction_territories WHERE territory_id = ?", (territory_id,))
                territory_data = cursor.fetchone()
                
                if not territory_data:
                    return {"success": False, "error": "Territory does not exist"}
                
                controlling_faction = territory_data[0]
                
                # Can only fight over territories controlled by the defender
                if controlling_faction != defender_faction_id and controlling_faction is not None:
                    return {"success": False, "error": "This territory is not controlled by the target faction"}
            
            # Take declaration cost from attacker's treasury
            cursor.execute("""
                UPDATE factions
                SET treasury = treasury - ?
                WHERE faction_id = ?
            """, (declaration_cost, attacker_faction_id))
            
            # Record war declaration in database
            war_duration_days = get_config("faction", "war_duration_days", 3)
            end_time = datetime.now() + timedelta(days=war_duration_days)
            
            cursor.execute("""
                INSERT INTO faction_wars (
                    attacker_faction_id, defender_faction_id, 
                    start_time, end_time, status, territory_id
                ) VALUES (?, ?, datetime('now'), ?, 'active', ?)
            """, (attacker_faction_id, defender_faction_id, end_time.isoformat(), territory_id))
            
            war_id = cursor.lastrowid
            
            # Add to faction history
            cursor.execute("""
                INSERT INTO faction_history (
                    faction_id, event_type, description, timestamp
                ) VALUES (?, 'war_declared', ?, datetime('now'))
            """, (attacker_faction_id, f"Declared war on {defender_name}"))
            
            cursor.execute("""
                INSERT INTO faction_history (
                    faction_id, event_type, description, timestamp
                ) VALUES (?, 'war_received', ?, datetime('now'))
            """, (defender_faction_id, f"War declared by {attacker_name}"))
            
            conn.commit()
            
            return {
                "success": True,
                "war_id": war_id,
                "attacker": attacker_name,
                "defender": defender_name,
                "territory_id": territory_id,
                "duration_days": war_duration_days,
                "end_time": end_time.isoformat(),
                "declaration_cost": declaration_cost
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    @staticmethod
    async def record_war_battle(
        war_id: int, 
        user_id: str, 
        faction_id: int, 
        opponent_user_id: Optional[str] = None,
        opponent_faction_id: Optional[int] = None,
        battle_type: str = "pvp",
        points: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record a battle in a faction war and award points.
        
        Args:
            war_id: ID of the war
            user_id: ID of the user who participated in the battle
            faction_id: ID of the user's faction
            opponent_user_id: Optional ID of the opponent user
            opponent_faction_id: Optional ID of the opponent's faction
            battle_type: Type of battle (pvp, pve, raid)
            points: Optional points override
            
        Returns:
            Dict: Result of the battle recording
        """
        # Security checks
        if not war_id or not user_id or not faction_id:
            return {"success": False, "error": "Missing required parameters"}
            
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify that the war exists and is active
            cursor.execute("""
                SELECT attacker_faction_id, defender_faction_id, status
                FROM faction_wars
                WHERE war_id = ?
            """, (war_id,))
            
            war_data = cursor.fetchone()
            if not war_data:
                return {"success": False, "error": "War not found"}
                
            attacker_id, defender_id, status = war_data
            
            if status != "active":
                return {"success": False, "error": "War is not active"}
                
            # Verify that the user is in one of the warring factions
            if faction_id != attacker_id and faction_id != defender_id:
                return {"success": False, "error": "User's faction is not involved in this war"}
                
            # Verify that the user is in the faction they claim
            cursor.execute("""
                SELECT COUNT(*) FROM faction_members
                WHERE user_id = ? AND faction_id = ?
            """, (user_id, faction_id))
            
            if cursor.fetchone()[0] == 0:
                return {"success": False, "error": "User is not in the specified faction"}
                
            # Check if opponent faction is involved in the war (if provided)
            if opponent_faction_id and opponent_faction_id != attacker_id and opponent_faction_id != defender_id:
                return {"success": False, "error": "Opponent faction is not involved in this war"}
                
            # Check for battle rate limiting to prevent exploits
            cursor.execute("""
                SELECT COUNT(*) FROM faction_war_battles
                WHERE war_id = ? AND user_id = ? AND timestamp > datetime('now', '-1 hour')
            """, (war_id, user_id))
            
            hourly_battles = cursor.fetchone()[0]
            max_hourly_battles = get_config("faction", "max_hourly_war_battles", 5)
            
            if hourly_battles >= max_hourly_battles:
                return {
                    "success": False, 
                    "error": f"Maximum of {max_hourly_battles} battles per hour. Try again later."
                }
                
            # Calculate points based on battle type if not provided
            if points is None:
                if battle_type == "pvp":
                    # PvP battles are worth more
                    base_points = get_config("faction", "war_pvp_points", 10)
                    points = base_points
                elif battle_type == "pve":
                    # PvE battles are worth less
                    base_points = get_config("faction", "war_pve_points", 5)
                    points = base_points
                elif battle_type == "raid":
                    # Raid battles are worth more
                    base_points = get_config("faction", "war_raid_points", 15)
                    points = base_points
                else:
                    # Default points
                    points = 5
                    
            # Cap points to prevent exploits
            max_points = get_config("faction", "max_war_battle_points", 20)
            points = min(points, max_points)
            
            # Record the battle
            cursor.execute("""
                INSERT INTO faction_war_battles (
                    war_id, user_id, faction_id, opponent_user_id, opponent_faction_id,
                    points_earned, battle_type, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                war_id, user_id, faction_id, opponent_user_id, 
                opponent_faction_id, points, battle_type
            ))
            
            # Update war score
            if faction_id == attacker_id:
                cursor.execute("""
                    UPDATE faction_wars
                    SET attacker_score = attacker_score + ?
                    WHERE war_id = ?
                """, (points, war_id))
            else:
                cursor.execute("""
                    UPDATE faction_wars
                    SET defender_score = defender_score + ?
                    WHERE war_id = ?
                """, (points, war_id))
                
            conn.commit()
            
            # Get updated scores
            cursor.execute("""
                SELECT attacker_score, defender_score
                FROM faction_wars
                WHERE war_id = ?
            """, (war_id,))
            
            attacker_score, defender_score = cursor.fetchone()
            
            return {
                "success": True,
                "battle_id": cursor.lastrowid,
                "points_earned": points,
                "attacker_score": attacker_score,
                "defender_score": defender_score
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    async def end_war(war_id: int) -> Dict[str, Any]:
        """
        End a faction war and determine the winner.
        
        Args:
            war_id: ID of the war to end
            
        Returns:
            Dict: Result of ending the war
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if the war exists and is active
            cursor.execute("""
                SELECT war_id, attacker_faction_id, defender_faction_id, 
                       attacker_score, defender_score, territory_id, status
                FROM faction_wars 
                WHERE war_id = ?
            """, (war_id,))
            
            war_data = cursor.fetchone()
            if not war_data:
                return {"success": False, "error": "War not found"}
                
            war_id, attacker_id, defender_id, attacker_score, defender_score, territory_id, status = war_data
            
            if status != "active":
                return {"success": False, "error": "War is already ended"}
            
            # Determine winner
            winner_id = None
            if attacker_score > defender_score:
                winner_id = attacker_id
            elif defender_score > attacker_score:
                winner_id = defender_id
            # If tied, defender holds their ground
            elif defender_score == attacker_score and territory_id:
                winner_id = defender_id
                
            # Update war status
            cursor.execute("""
                UPDATE faction_wars 
                SET status = 'ended', end_time = datetime('now'), winner_faction_id = ? 
                WHERE war_id = ?
            """, (winner_id, war_id))
            
            # Handle territory control if this was a territory war
            territory_result = None
            if territory_id and winner_id:
                cursor.execute("""
                    UPDATE faction_territories 
                    SET controlling_faction_id = ?, capture_date = datetime('now') 
                    WHERE territory_id = ?
                """, (winner_id, territory_id))
                
                # Get territory details for the response
                cursor.execute("""
                    SELECT name, daily_token_bonus, daily_xp_bonus 
                    FROM faction_territories 
                    WHERE territory_id = ?
                """, (territory_id,))
                
                territory_info = cursor.fetchone()
                if territory_info:
                    territory_name, token_bonus, xp_bonus = territory_info
                    territory_result = {
                        "territory_id": territory_id,
                        "name": territory_name,
                        "daily_token_bonus": token_bonus,
                        "daily_xp_bonus": xp_bonus,
                        "new_controller": winner_id
                    }
            
            # Award spoils of war
            faction_economy = get_faction_economy()
            xp_reward = get_config("faction_war", "victory_xp", 5000)
            token_reward = get_config("faction_war", "victory_tokens", 20000)
            
            reward_result = None
            if winner_id:
                # Award XP
                xp_result = await faction_economy.add_faction_xp(winner_id, xp_reward)
                
                # Award tokens to treasury
                cursor.execute("""
                    UPDATE factions 
                    SET treasury = treasury + ? 
                    WHERE faction_id = ?
                """, (token_reward, winner_id))
                
                reward_result = {
                    "xp_reward": xp_reward,
                    "token_reward": token_reward,
                    "level_up": xp_result.get("level_up", False) if isinstance(xp_result, dict) else False
                }
                
                # Record this in faction history
                if attacker_id == winner_id:
                    loser_id = defender_id
                else:
                    loser_id = attacker_id
                    
                cursor.execute("""
                    INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                    VALUES (?, 'war_victory', ?, datetime('now'))
                """, (winner_id, f"Won war against faction {loser_id}"))
                
                cursor.execute("""
                    INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                    VALUES (?, 'war_defeat', ?, datetime('now'))
                """, (loser_id, f"Lost war against faction {winner_id}"))
            else:
                # It was a tie with no territory involved
                cursor.execute("""
                    INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                    VALUES (?, 'war_draw', ?, datetime('now'))
                """, (attacker_id, f"War with faction {defender_id} ended in a draw"))
                
                cursor.execute("""
                    INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                    VALUES (?, 'war_draw', ?, datetime('now'))
                """, (defender_id, f"War with faction {attacker_id} ended in a draw"))
            
            conn.commit()
            
            # Get faction names for the response
            cursor.execute("SELECT faction_id, name FROM factions WHERE faction_id IN (?, ?)", 
                          (attacker_id, defender_id))
            faction_names = {faction_id: name for faction_id, name in cursor.fetchall()}
            
            return {
                "success": True,
                "war_id": war_id,
                "attacker": {
                    "faction_id": attacker_id,
                    "name": faction_names.get(attacker_id, f"Faction {attacker_id}"),
                    "score": attacker_score
                },
                "defender": {
                    "faction_id": defender_id,
                    "name": faction_names.get(defender_id, f"Faction {defender_id}"),
                    "score": defender_score
                },
                "winner": winner_id,
                "winner_name": faction_names.get(winner_id, None) if winner_id else "Draw",
                "territory": territory_result,
                "rewards": reward_result
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    async def get_active_wars() -> List[Dict[str, Any]]:
        """
        Get a list of all active faction wars.
        
        Returns:
            List[Dict]: Active faction wars
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT w.war_id, w.attacker_faction_id, w.defender_faction_id, 
                       w.start_time, w.end_time, w.attacker_score, w.defender_score,
                       a.name as attacker_name, d.name as defender_name,
                       t.territory_id, t.name as territory_name
                FROM faction_wars w
                JOIN factions a ON w.attacker_faction_id = a.faction_id
                JOIN factions d ON w.defender_faction_id = d.faction_id
                LEFT JOIN faction_territories t ON w.territory_id = t.territory_id
                WHERE w.status = 'active'
                ORDER BY w.end_time ASC
            """)
            
            wars = []
            for row in cursor.fetchall():
                (war_id, attacker_id, defender_id, start_time, end_time, 
                attacker_score, defender_score, attacker_name, defender_name, 
                territory_id, territory_name) = row
                
                wars.append({
                    "war_id": war_id,
                    "attacker": {
                        "faction_id": attacker_id,
                        "name": attacker_name,
                        "score": attacker_score
                    },
                    "defender": {
                        "faction_id": defender_id,
                        "name": defender_name,
                        "score": defender_score
                    },
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_remaining": (datetime.fromisoformat(end_time) - datetime.now()).total_seconds() if end_time else None,
                    "territory": {
                        "territory_id": territory_id,
                        "name": territory_name
                    } if territory_id else None
                })
                
            return wars
        finally:
            conn.close()
    
    @staticmethod
    async def get_territories() -> List[Dict[str, Any]]:
        """
        Get a list of all territories and their current controllers.
        
        Returns:
            List[Dict]: Territory information
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT t.territory_id, t.name, t.description, t.controlling_faction_id,
                       t.daily_token_bonus, t.daily_xp_bonus, t.biome_type,
                       t.exclusive_veramon, t.defense_value, t.capture_date,
                       f.name as faction_name, f.color as faction_color
                FROM faction_territories t
                LEFT JOIN factions f ON t.controlling_faction_id = f.faction_id
                ORDER BY t.name ASC
            """)
            
            territories = []
            for row in cursor.fetchall():
                (territory_id, name, description, controlling_faction_id,
                daily_token_bonus, daily_xp_bonus, biome_type,
                exclusive_veramon, defense_value, capture_date,
                faction_name, faction_color) = row
                
                territories.append({
                    "territory_id": territory_id,
                    "name": name,
                    "description": description,
                    "controlling_faction": {
                        "faction_id": controlling_faction_id,
                        "name": faction_name,
                        "color": faction_color
                    } if controlling_faction_id else None,
                    "daily_token_bonus": daily_token_bonus,
                    "daily_xp_bonus": daily_xp_bonus,
                    "biome_type": biome_type,
                    "exclusive_veramon": exclusive_veramon.split(",") if exclusive_veramon else [],
                    "defense_value": defense_value,
                    "capture_date": capture_date
                })
                
            return territories
        finally:
            conn.close()
    
    @staticmethod
    async def claim_territory_rewards() -> Dict[str, Any]:
        """
        Process and distribute daily rewards for territories.
        This should be called once per day by a scheduled task.
        
        Returns:
            Dict: Results of territory reward distribution
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get all territories with controlling factions
            cursor.execute("""
                SELECT t.territory_id, t.controlling_faction_id,
                       t.daily_token_bonus, t.daily_xp_bonus, f.name as faction_name
                FROM faction_territories t
                JOIN factions f ON t.controlling_faction_id = f.faction_id
                WHERE t.controlling_faction_id IS NOT NULL
            """)
            
            rewards_by_faction = {}
            territories_processed = []
            
            for row in cursor.fetchall():
                territory_id, faction_id, token_bonus, xp_bonus, faction_name = row
                
                # Add tokens to faction treasury
                cursor.execute("""
                    UPDATE factions
                    SET treasury = treasury + ?
                    WHERE faction_id = ?
                """, (token_bonus, faction_id))
                
                # Track rewards by faction for summary
                if faction_id not in rewards_by_faction:
                    rewards_by_faction[faction_id] = {
                        "faction_id": faction_id,
                        "faction_name": faction_name,
                        "total_tokens": 0,
                        "total_xp": 0,
                        "territories": []
                    }
                
                rewards_by_faction[faction_id]["total_tokens"] += token_bonus
                rewards_by_faction[faction_id]["total_xp"] += xp_bonus
                rewards_by_faction[faction_id]["territories"].append({
                    "territory_id": territory_id,
                    "tokens": token_bonus,
                    "xp": xp_bonus
                })
                
                territories_processed.append(territory_id)
            
            # Process XP rewards
            faction_economy = get_faction_economy()
            for faction_id, reward_info in rewards_by_faction.items():
                xp_result = await faction_economy.add_faction_xp(faction_id, reward_info["total_xp"])
                reward_info["level_up"] = xp_result.get("level_up", False) if isinstance(xp_result, dict) else False
                
                # Add record to faction history
                cursor.execute("""
                    INSERT INTO faction_history (faction_id, event_type, description, timestamp)
                    VALUES (?, 'territory_rewards', ?, datetime('now'))
                """, (faction_id, f"Received {reward_info['total_tokens']} tokens and {reward_info['total_xp']} XP from controlled territories"))
            
            conn.commit()
            
            return {
                "success": True,
                "territories_processed": len(territories_processed),
                "rewards_by_faction": list(rewards_by_faction.values())
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    @staticmethod
    def check_war_security(user_id: str, faction_id: int) -> bool:
        """
        Check if a user has permission to manage wars for their faction.
        
        Args:
            user_id: ID of the user
            faction_id: ID of the faction
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check user's rank in the faction
            cursor.execute("""
                SELECT fm.rank_id, fr.can_manage_wars
                FROM faction_members fm
                JOIN faction_ranks fr ON fm.faction_id = fr.faction_id AND fm.rank_id = fr.rank_id
                WHERE fm.user_id = ? AND fm.faction_id = ?
            """, (user_id, faction_id))
            
            result = cursor.fetchone()
            if not result:
                return False
                
            rank_id, can_manage_wars = result
            
            return can_manage_wars == 1
        finally:
            conn.close()

# Singleton instance
_faction_war = None

def get_faction_war() -> FactionWar:
    """
    Get the global faction war instance.
    
    Returns:
        FactionWar: Global faction war instance
    """
    global _faction_war
    
    if _faction_war is None:
        _faction_war = FactionWar()
        
    return _faction_war
