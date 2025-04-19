"""
Database initialization for faction economy system.

This module initializes all database tables required for the faction economy system,
including faction shops, leveling, and contributions.
"""

import json
import os
from src.db.db import get_connection
from src.utils.config_manager import get_config


def initialize_faction_economy_db():
    """
    Initialize all database tables for faction economy system.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Update factions table to include economy-related columns
    cursor.execute("""
    ALTER TABLE factions ADD COLUMN IF NOT EXISTS treasury INTEGER DEFAULT 0
    """)
    
    cursor.execute("""
    ALTER TABLE factions ADD COLUMN IF NOT EXISTS faction_xp INTEGER DEFAULT 0
    """)
    
    cursor.execute("""
    ALTER TABLE factions ADD COLUMN IF NOT EXISTS faction_level INTEGER DEFAULT 1
    """)
    
    # Create faction_shop_items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_shop_items (
        item_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        price INTEGER NOT NULL,
        required_level INTEGER DEFAULT 1,
        category TEXT NOT NULL,
        effects TEXT,
        availability TEXT DEFAULT 'all',
        image_url TEXT
    )
    """)
    
    # Create faction_purchase_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_purchase_history (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        total_price INTEGER NOT NULL,
        purchase_date TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (item_id) REFERENCES faction_shop_items(item_id)
    )
    """)
    
    # Create faction_contributions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_contributions (
        contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        amount INTEGER NOT NULL,
        contribution_type TEXT DEFAULT 'tokens',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # Create faction_events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_data TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
    )
    """)
    
    # Create faction_buffs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_buffs (
        buff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        buff_type TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        activated_by TEXT NOT NULL,
        strength REAL DEFAULT 1.0,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id),
        FOREIGN KEY (activated_by) REFERENCES users(user_id)
    )
    """)
    
    # Create faction_purchased_upgrades table (for permanent upgrades)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_purchased_upgrades (
        faction_id INTEGER NOT NULL,
        upgrade_id TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        last_upgraded_by TEXT NOT NULL,
        last_upgraded_at TEXT NOT NULL,
        PRIMARY KEY (faction_id, upgrade_id),
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id),
        FOREIGN KEY (last_upgraded_by) REFERENCES users(user_id)
    )
    """)
    
    # Create faction_upgrades reference table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_upgrades (
        upgrade_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        base_cost INTEGER NOT NULL,
        cost_scaling REAL DEFAULT 1.5,
        max_level INTEGER DEFAULT 10,
        effect_per_level REAL NOT NULL,
        effect_type TEXT NOT NULL
    )
    """)
    
    # Update faction_members table to track member contributions
    cursor.execute("""
    ALTER TABLE faction_members ADD COLUMN IF NOT EXISTS total_contributions INTEGER DEFAULT 0
    """)
    
    # Create indices for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_shop_level ON faction_shop_items(required_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_shop_category ON faction_shop_items(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_contributions_user ON faction_contributions(faction_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_buffs_end_time ON faction_buffs(faction_id, end_time)")
    
    conn.commit()
    
    # Check if we need to populate the faction_shop_items table with default items
    cursor.execute("SELECT COUNT(*) FROM faction_shop_items")
    if cursor.fetchone()[0] == 0:
        # Load default shop items
        populate_default_shop_items(cursor)
        populate_default_faction_upgrades(cursor)
        conn.commit()
    
    conn.close()


def populate_default_shop_items(cursor):
    """
    Populate the faction_shop_items table with default items.
    """
    default_items = [
        # Level 1 Items
        {
            "item_id": "faction_token_booster",
            "name": "Token Booster",
            "description": "Increases token gains by 20% for all faction members for 24 hours",
            "price": 1000,
            "required_level": 1,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "token",
                "strength": 1.2,
                "duration": 24
            }),
            "image_url": "https://i.imgur.com/abc123.png"
        },
        {
            "item_id": "faction_healing_kit",
            "name": "Faction Healing Kit",
            "description": "Heals all your Veramon to full HP. Faction-exclusive item.",
            "price": 150,
            "required_level": 1,
            "category": "consumable",
            "effects": json.dumps({
                "effect_type": "heal_all",
                "strength": 1.0
            }),
            "image_url": "https://i.imgur.com/xyz456.png"
        },
        
        # Level 2 Items
        {
            "item_id": "faction_xp_booster",
            "name": "XP Booster",
            "description": "Increases XP gains by 25% for all faction members for 24 hours",
            "price": 2000,
            "required_level": 2,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "xp",
                "strength": 1.25,
                "duration": 24
            }),
            "image_url": "https://i.imgur.com/def456.png"
        },
        
        # Level 3 Items
        {
            "item_id": "faction_catch_booster",
            "name": "Catch Rate Booster",
            "description": "Increases catch rate by 15% for all faction members for 24 hours",
            "price": 3000,
            "required_level": 3,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "catch",
                "strength": 1.15,
                "duration": 24
            }),
            "image_url": "https://i.imgur.com/ghi789.png"
        },
        {
            "item_id": "faction_badge_box",
            "name": "Faction Badge Box",
            "description": "Contains a random badge with faction emblem. Chance for rare badges.",
            "price": 2500,
            "required_level": 3,
            "category": "consumable",
            "effects": json.dumps({
                "effect_type": "random_badge",
                "faction_branded": True
            }),
            "image_url": "https://i.imgur.com/jkl012.png"
        },
        
        # Level 5 Items
        {
            "item_id": "faction_shiny_booster",
            "name": "Shiny Chance Booster",
            "description": "Doubles shiny encounter rate for all faction members for 24 hours",
            "price": 7500,
            "required_level": 5,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "shiny",
                "strength": 2.0,
                "duration": 24
            }),
            "image_url": "https://i.imgur.com/mno345.png"
        },
        {
            "item_id": "faction_evolution_booster",
            "name": "Evolution Cost Reducer",
            "description": "Reduces evolution costs by 50% for all faction members for 24 hours",
            "price": 5000,
            "required_level": 5,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "evolution",
                "strength": 0.5,
                "duration": 24
            }),
            "image_url": "https://i.imgur.com/pqr678.png"
        },
        
        # Level 7 Items
        {
            "item_id": "faction_territory_scanner",
            "name": "Territory Scanner",
            "description": "Scan for available territories to claim for your faction",
            "price": 10000,
            "required_level": 7,
            "category": "consumable",
            "effects": json.dumps({
                "effect_type": "territory_scan",
                "scan_radius": 3
            }),
            "image_url": "https://i.imgur.com/stu901.png"
        },
        
        # Level 10 Items
        {
            "item_id": "faction_legendary_bait",
            "name": "Legendary Bait",
            "description": "Increases chance of encountering legendary Veramon for the entire faction for 12 hours",
            "price": 25000,
            "required_level": 10,
            "category": "buff",
            "effects": json.dumps({
                "buff_type": "legendary",
                "strength": 3.0,
                "duration": 12
            }),
            "image_url": "https://i.imgur.com/vwx234.png"
        },
        {
            "item_id": "faction_upgrade_token_gain",
            "name": "Token Economy Upgrade",
            "description": "Permanently increases token gains for all faction members by 5% per level",
            "price": 20000,
            "required_level": 10,
            "category": "upgrade",
            "effects": json.dumps({
                "upgrade_id": "token_economy",
                "effect_type": "token_multiplier"
            }),
            "image_url": "https://i.imgur.com/yza567.png"
        }
    ]
    
    # Insert default items
    for item in default_items:
        cursor.execute("""
            INSERT OR IGNORE INTO faction_shop_items
            (item_id, name, description, price, required_level, category, effects, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["item_id"],
            item["name"],
            item["description"],
            item["price"],
            item["required_level"],
            item["category"],
            item["effects"],
            item["image_url"]
        ))


def populate_default_faction_upgrades(cursor):
    """
    Populate the faction_upgrades table with default upgrades.
    """
    default_upgrades = [
        {
            "upgrade_id": "token_economy",
            "name": "Token Economy",
            "description": "Permanently increases token gains for all faction members",
            "base_cost": 20000,
            "cost_scaling": 1.5,
            "max_level": 10,
            "effect_per_level": 0.05,
            "effect_type": "token_multiplier"
        },
        {
            "upgrade_id": "xp_boost",
            "name": "XP Enhancement",
            "description": "Permanently increases XP gains for all faction members",
            "base_cost": 25000,
            "cost_scaling": 1.5,
            "max_level": 10,
            "effect_per_level": 0.05,
            "effect_type": "xp_multiplier"
        },
        {
            "upgrade_id": "catch_rate",
            "name": "Capture Technology",
            "description": "Permanently increases catch rate for all faction members",
            "base_cost": 30000,
            "cost_scaling": 1.6,
            "max_level": 5,
            "effect_per_level": 0.03,
            "effect_type": "catch_rate"
        },
        {
            "upgrade_id": "treasury_capacity",
            "name": "Treasury Expansion",
            "description": "Increases maximum treasury capacity",
            "base_cost": 15000,
            "cost_scaling": 1.4,
            "max_level": 20,
            "effect_per_level": 50000,
            "effect_type": "treasury_capacity"
        },
        {
            "upgrade_id": "member_capacity",
            "name": "Member Expansion",
            "description": "Increases maximum faction member capacity",
            "base_cost": 50000,
            "cost_scaling": 2.0,
            "max_level": 5,
            "effect_per_level": 5,
            "effect_type": "member_capacity"
        }
    ]
    
    # Insert default upgrades
    for upgrade in default_upgrades:
        cursor.execute("""
            INSERT OR IGNORE INTO faction_upgrades
            (upgrade_id, name, description, base_cost, cost_scaling, max_level, effect_per_level, effect_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            upgrade["upgrade_id"],
            upgrade["name"],
            upgrade["description"],
            upgrade["base_cost"],
            upgrade["cost_scaling"],
            upgrade["max_level"],
            upgrade["effect_per_level"],
            upgrade["effect_type"]
        ))
