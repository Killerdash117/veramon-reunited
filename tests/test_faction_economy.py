"""
Unit tests for the faction economy system.

These tests ensure the faction economy system works correctly and
doesn't contain any security vulnerabilities or exploits.
"""

import unittest
import sqlite3
import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.faction_economy import FactionEconomy, get_faction_economy
from src.db.db import get_connection

class TestFactionEconomy(unittest.TestCase):
    """Tests for the faction economy system."""
    
    def setUp(self):
        """Set up an in-memory database for testing."""
        # Create a test database connection
        self.original_get_connection = get_connection
        
        # Mock the database connection to use an in-memory database
        def mock_get_connection():
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            return conn
            
        # Apply the mock
        get_connection.__code__ = mock_get_connection.__code__
        
        # Set up the test database schema
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create factions table
        cursor.execute("""
        CREATE TABLE factions (
            faction_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT DEFAULT '0099FF',
            faction_xp INTEGER DEFAULT 0,
            faction_level INTEGER DEFAULT 1,
            treasury INTEGER DEFAULT 0,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            leader_id TEXT,
            member_count INTEGER DEFAULT 0
        )
        """)
        
        # Create faction_members table
        cursor.execute("""
        CREATE TABLE faction_members (
            faction_id INTEGER,
            user_id TEXT,
            rank_id INTEGER DEFAULT 1,
            joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (faction_id, user_id)
        )
        """)
        
        # Create faction_contributions table
        cursor.execute("""
        CREATE TABLE faction_contributions (
            contribution_id INTEGER PRIMARY KEY,
            faction_id INTEGER,
            user_id TEXT,
            amount INTEGER,
            contribution_type TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create faction_ranks table
        cursor.execute("""
        CREATE TABLE faction_ranks (
            faction_id INTEGER,
            rank_id INTEGER,
            name TEXT,
            can_invite INTEGER DEFAULT 0,
            can_kick INTEGER DEFAULT 0,
            can_manage_ranks INTEGER DEFAULT 0,
            can_manage_treasury INTEGER DEFAULT 0,
            can_manage_shop INTEGER DEFAULT 0,
            can_manage_wars INTEGER DEFAULT 0,
            autorank_contribution INTEGER DEFAULT 0,
            PRIMARY KEY (faction_id, rank_id)
        )
        """)
        
        # Create faction_shop_items table
        cursor.execute("""
        CREATE TABLE faction_shop_items (
            item_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            effect TEXT,
            multiplier REAL,
            duration INTEGER,
            uses INTEGER,
            category TEXT,
            required_level INTEGER DEFAULT 1
        )
        """)
        
        # Create faction_shop_purchases table
        cursor.execute("""
        CREATE TABLE faction_shop_purchases (
            purchase_id INTEGER PRIMARY KEY,
            faction_id INTEGER,
            user_id TEXT,
            item_id TEXT,
            price_paid INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            uses_remaining INTEGER,
            duration INTEGER,
            multiplier REAL
        )
        """)
        
        # Create users table
        cursor.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            tokens INTEGER DEFAULT 0,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create faction_history table
        cursor.execute("""
        CREATE TABLE faction_history (
            history_id INTEGER PRIMARY KEY,
            faction_id INTEGER,
            user_id TEXT,
            event_type TEXT,
            description TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Insert test data
        cursor.execute("""
        INSERT INTO factions (faction_id, name, faction_xp, faction_level, treasury)
        VALUES (1, 'Test Faction', 100, 1, 5000)
        """)
        
        cursor.execute("""
        INSERT INTO users (user_id, username, tokens)
        VALUES ('123456', 'TestUser', 10000)
        """)
        
        cursor.execute("""
        INSERT INTO faction_members (faction_id, user_id, rank_id)
        VALUES (1, '123456', 1)
        """)
        
        cursor.execute("""
        INSERT INTO faction_ranks (faction_id, rank_id, name, can_manage_treasury)
        VALUES (1, 1, 'Member', 1)
        """)
        
        cursor.execute("""
        INSERT INTO faction_ranks (faction_id, rank_id, name, can_manage_treasury, autorank_contribution)
        VALUES (1, 2, 'Officer', 1, 5000)
        """)
        
        # Insert test faction shop items
        cursor.execute("""
        INSERT INTO faction_shop_items (item_id, name, description, price, effect, multiplier, duration, category, required_level)
        VALUES ('faction_token_booster', 'Token Booster', 'Boosts token gains for all members', 5000, 'faction_token_boost', 1.25, 86400, 'buff', 1)
        """)
        
        cursor.execute("""
        INSERT INTO faction_shop_items (item_id, name, description, price, effect, multiplier, duration, category, required_level)
        VALUES ('faction_xp_booster', 'XP Booster', 'Boosts XP gains for all members', 5000, 'faction_xp_boost', 1.25, 86400, 'buff', 1)
        """)
        
        cursor.execute("""
        INSERT INTO faction_shop_items (item_id, name, description, price, effect, uses, category, required_level)
        VALUES ('faction_territory_banner', 'Territory Banner', 'Claim a territory', 25000, 'territory_claim', 1, 'upgrade', 5)
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize the faction economy
        self.faction_economy = FactionEconomy()
        
    def tearDown(self):
        """Restore the original connection function."""
        get_connection.__code__ = self.original_get_connection.__code__
    
    async def test_get_faction_level(self):
        """Test getting a faction's level and XP."""
        level, xp, next_xp = self.faction_economy.get_faction_level(1)
        
        self.assertEqual(level, 1)
        self.assertEqual(xp, 100)
        self.assertGreater(next_xp, xp)
    
    async def test_calculate_xp_for_level(self):
        """Test calculating XP required for a level."""
        # Level 1 should require 100 XP
        xp_level_1 = self.faction_economy.calculate_xp_for_level(1)
        self.assertEqual(xp_level_1, 100)
        
        # Level 2 should require more than level 1
        xp_level_2 = self.faction_economy.calculate_xp_for_level(2)
        self.assertGreater(xp_level_2, xp_level_1)
        
        # Higher levels should require exponentially more XP
        xp_level_10 = self.faction_economy.calculate_xp_for_level(10)
        self.assertGreater(xp_level_10 / xp_level_2, xp_level_2 / xp_level_1)
    
    async def test_add_faction_xp(self):
        """Test adding XP to a faction."""
        # Add 1000 XP to the faction
        result = await self.faction_economy.add_faction_xp(1, 1000)
        
        self.assertTrue(result["success"])
        
        # Verify the XP was added
        level, xp, next_xp = self.faction_economy.get_faction_level(1)
        self.assertEqual(xp, 1100)  # 100 (initial) + 1000 (added)
    
    async def test_level_up(self):
        """Test faction leveling up when XP threshold is reached."""
        # Get XP required for level 2
        level_2_xp = self.faction_economy.calculate_xp_for_level(2)
        
        # Add enough XP to level up
        result = await self.faction_economy.add_faction_xp(1, level_2_xp)
        
        self.assertTrue(result["success"])
        
        # Verify the faction leveled up
        level, xp, next_xp = self.faction_economy.get_faction_level(1)
        self.assertEqual(level, 2)
    
    async def test_get_faction_shop_items(self):
        """Test getting faction shop items based on level."""
        # Get items available at level 1
        items = self.faction_economy.get_faction_shop_items(1)
        
        # Should include faction_token_booster and faction_xp_booster (level 1 items)
        item_ids = [item["item_id"] for item in items]
        self.assertIn("faction_token_booster", item_ids)
        self.assertIn("faction_xp_booster", item_ids)
        
        # territory_banner should be in the list but marked as not available
        territory_banner = next((item for item in items if item["item_id"] == "faction_territory_banner"), None)
        self.assertIsNotNone(territory_banner)
        self.assertFalse(territory_banner["available"])
        
        # Get items available at level 5
        items = self.faction_economy.get_faction_shop_items(5)
        territory_banner = next((item for item in items if item["item_id"] == "faction_territory_banner"), None)
        self.assertIsNotNone(territory_banner)
        self.assertTrue(territory_banner["available"])
    
    async def test_purchase_faction_item(self):
        """Test purchasing an item from the faction shop."""
        # Set up the test
        conn = get_connection()
        cursor = conn.cursor()
        
        # Add more tokens to the treasury
        cursor.execute("UPDATE factions SET treasury = 10000 WHERE faction_id = 1")
        conn.commit()
        conn.close()
        
        # Purchase an item
        result = await self.faction_economy.purchase_faction_item(
            user_id="123456",
            faction_id=1,
            item_id="faction_token_booster",
            quantity=1
        )
        
        self.assertTrue(result["success"])
        
        # Verify the purchase was recorded
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM faction_shop_purchases
            WHERE faction_id = 1 AND item_id = 'faction_token_booster'
        """)
        purchase_count = cursor.fetchone()[0]
        self.assertEqual(purchase_count, 1)
        
        # Verify treasury was deducted
        cursor.execute("SELECT treasury FROM factions WHERE faction_id = 1")
        treasury = cursor.fetchone()[0]
        self.assertEqual(treasury, 5000)  # 10000 - 5000 (item price)
        
        conn.close()
    
    async def test_contribute_to_treasury(self):
        """Test contributing tokens to the faction treasury."""
        # Contribute 2000 tokens
        result = await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=2000
        )
        
        self.assertTrue(result["success"])
        
        # Verify the contribution was recorded
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM faction_contributions
            WHERE faction_id = 1 AND user_id = '123456' AND amount = 2000
        """)
        contribution_count = cursor.fetchone()[0]
        self.assertEqual(contribution_count, 1)
        
        # Verify treasury was increased
        cursor.execute("SELECT treasury FROM factions WHERE faction_id = 1")
        treasury = cursor.fetchone()[0]
        self.assertEqual(treasury, 7000)  # 5000 + 2000
        
        # Verify user tokens were deducted
        cursor.execute("SELECT tokens FROM users WHERE user_id = '123456'")
        tokens = cursor.fetchone()[0]
        self.assertEqual(tokens, 8000)  # 10000 - 2000
        
        conn.close()
    
    async def test_contribute_insufficient_tokens(self):
        """Test contributing more tokens than the user has."""
        # Try to contribute more tokens than the user has
        result = await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=15000  # User only has 10000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Insufficient tokens", result["error"])
    
    async def test_contribution_milestone_reward(self):
        """Test getting a reward when reaching a contribution milestone."""
        # Contribute 4900 tokens first
        await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=4900
        )
        
        # Now contribute 100 more to reach the 5000 milestone
        result = await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=100
        )
        
        self.assertTrue(result["success"])
        self.assertIsNotNone(result.get("milestone_reward"))
        self.assertEqual(result["milestone_reward"]["threshold"], 5000)
        
        # Verify user got the token reward
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tokens FROM users WHERE user_id = '123456'")
        tokens = cursor.fetchone()[0]
        
        # Original: 10000 - 4900 - 100 + milestone reward
        expected_tokens = 10000 - 4900 - 100 + result["milestone_reward"]["tokens"]
        self.assertEqual(tokens, expected_tokens)
        conn.close()
    
    async def test_rank_promotion(self):
        """Test getting promoted when reaching a contribution threshold."""
        # Contribute enough to reach rank promotion threshold
        result = await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=5000
        )
        
        self.assertTrue(result["success"])
        self.assertIsNotNone(result.get("rank_promotion"))
        self.assertEqual(result["rank_promotion"]["rank_id"], 2)
        self.assertEqual(result["rank_promotion"]["rank_name"], "Officer")
        
        # Verify user's rank was updated
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rank_id FROM faction_members
            WHERE faction_id = 1 AND user_id = '123456'
        """)
        rank_id = cursor.fetchone()[0]
        self.assertEqual(rank_id, 2)
        conn.close()
    
    async def test_get_faction_contribution_leaderboard(self):
        """Test getting the faction contribution leaderboard."""
        # Add multiple contributions
        await self.faction_economy.contribute_to_treasury("123456", 1, 1000)
        
        # Add another user
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, tokens)
            VALUES ('789012', 'TestUser2', 10000)
        """)
        cursor.execute("""
            INSERT INTO faction_members (faction_id, user_id, rank_id)
            VALUES (1, '789012', 1)
        """)
        conn.commit()
        conn.close()
        
        await self.faction_economy.contribute_to_treasury("789012", 1, 2000)
        
        # Get leaderboard
        leaderboard = self.faction_economy.get_faction_contribution_leaderboard(1)
        
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]["user_id"], "789012")  # Highest contribution first
        self.assertEqual(leaderboard[0]["total_contribution"], 2000)
        self.assertEqual(leaderboard[1]["user_id"], "123456")
        self.assertEqual(leaderboard[1]["total_contribution"], 1000)

    async def test_security_negative_contribution(self):
        """Test security: ensure negative contributions are not allowed."""
        # Try to contribute a negative amount
        result = await self.faction_economy.contribute_to_treasury(
            user_id="123456",
            faction_id=1,
            amount=-1000
        )
        
        self.assertFalse(result["success"])
    
    async def test_security_faction_membership(self):
        """Test security: ensure only faction members can contribute."""
        # Create a user who is not in the faction
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, tokens)
            VALUES ('999999', 'NonMember', 10000)
        """)
        conn.commit()
        conn.close()
        
        # Try to contribute from a non-member
        result = await self.faction_economy.contribute_to_treasury(
            user_id="999999",
            faction_id=1,
            amount=1000
        )
        
        self.assertFalse(result["success"])
        self.assertIn("not a member", result["error"])
    
    async def test_security_item_level_requirement(self):
        """Test security: ensure items require proper level to purchase."""
        # Try to buy a higher-level item
        result = await self.faction_economy.purchase_faction_item(
            user_id="123456",
            faction_id=1,
            item_id="faction_territory_banner"  # Requires level 5
        )
        
        self.assertFalse(result["success"])
        self.assertIn("required level", result["error"])

if __name__ == '__main__':
    unittest.main()
