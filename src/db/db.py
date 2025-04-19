import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "veramon.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS captures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        veramon_name TEXT NOT NULL,
        caught_at TEXT NOT NULL,
        shiny INTEGER NOT NULL,
        biome TEXT NOT NULL,
        nickname TEXT,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        active INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        PRIMARY KEY (user_id, item_id)
    )
    """)
    # Users table for economy, XP, and achievements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        tokens INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        achievements TEXT DEFAULT '[]',
        challenges_completed INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        guild_id INTEGER,
        faction_id INTEGER,
        last_daily_bonus TEXT,
        title TEXT,
        profile_theme TEXT DEFAULT 'default'
    )
    """)
    
    # Veramon movesets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS veramon_movesets (
        capture_id INTEGER NOT NULL,
        move_slot INTEGER NOT NULL,
        move_id TEXT NOT NULL,
        pp_remaining INTEGER NOT NULL,
        PRIMARY KEY (capture_id, move_slot),
        FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
    )
    """)
    
    # Guilds table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        leader_id TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        max_members INTEGER DEFAULT 5
    )
    """)
    
    # Guild members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guild_members (
        guild_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        role TEXT DEFAULT 'member',
        PRIMARY KEY (guild_id, user_id),
        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
    )
    """)
    
    # Factions table - large-scale organizations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factions (
        faction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        leader_id TEXT NOT NULL,
        description TEXT,
        motto TEXT,
        emblem_url TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        tokens INTEGER DEFAULT 0,
        member_capacity INTEGER DEFAULT 50,
        color TEXT DEFAULT '0099ff'
    )
    """)
    
    # Faction ranks table - rank definitions within a faction
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_ranks (
        rank_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        level INTEGER NOT NULL,
        permissions TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE
    )
    """)
    
    # Faction members table - tracks all members of factions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_members (
        faction_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        rank_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        contribution INTEGER DEFAULT 0,
        last_active TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (faction_id, user_id),
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE,
        FOREIGN KEY (rank_id) REFERENCES faction_ranks(rank_id) ON DELETE CASCADE
    )
    """)
    
    # Faction upgrades table - all possible faction upgrades
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_upgrades (
        upgrade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        cost INTEGER NOT NULL,
        max_level INTEGER NOT NULL,
        upgrade_type TEXT NOT NULL,
        effect_per_level REAL NOT NULL
    )
    """)
    
    # Faction purchased upgrades - tracks which upgrades each faction has purchased
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_purchased_upgrades (
        faction_id INTEGER NOT NULL,
        upgrade_id INTEGER NOT NULL,
        level INTEGER NOT NULL DEFAULT 1,
        purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (faction_id, upgrade_id),
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE,
        FOREIGN KEY (upgrade_id) REFERENCES faction_upgrades(upgrade_id) ON DELETE CASCADE
    )
    """)
    
    # Faction wars - tracks ongoing faction vs. faction competitions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_wars (
        war_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction1_id INTEGER NOT NULL,
        faction2_id INTEGER NOT NULL,
        start_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time TEXT NOT NULL,
        faction1_score INTEGER DEFAULT 0,
        faction2_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        reward_pool INTEGER DEFAULT 0,
        war_type TEXT DEFAULT 'standard',
        FOREIGN KEY (faction1_id) REFERENCES factions(faction_id) ON DELETE CASCADE,
        FOREIGN KEY (faction2_id) REFERENCES factions(faction_id) ON DELETE CASCADE
    )
    """)
    
    # Faction territories - areas that factions can control
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_territories (
        territory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        controlling_faction_id INTEGER,
        capture_date TEXT,
        resource_type TEXT NOT NULL,
        resource_amount INTEGER NOT NULL,
        cooldown_ends TEXT,
        FOREIGN KEY (controlling_faction_id) REFERENCES factions(faction_id) ON DELETE SET NULL
    )
    """)
    
    # Faction raid events - special PvE challenges for factions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_raids (
        raid_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        boss_name TEXT NOT NULL,
        boss_hp INTEGER NOT NULL,
        status TEXT DEFAULT 'scheduled',
        reward_tokens INTEGER NOT NULL,
        reward_xp INTEGER NOT NULL,
        min_participants INTEGER DEFAULT 10
    )
    """)
    
    # Faction raid participants - tracks which factions are participating in raids
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_raid_participants (
        raid_id INTEGER NOT NULL,
        faction_id INTEGER NOT NULL,
        join_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        damage_dealt INTEGER DEFAULT 0,
        status TEXT DEFAULT 'joined',
        PRIMARY KEY (raid_id, faction_id),
        FOREIGN KEY (raid_id) REFERENCES faction_raids(raid_id) ON DELETE CASCADE,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE
    )
    """)
    
    # Insert default faction upgrades
    cursor.execute("SELECT COUNT(*) FROM faction_upgrades")
    if cursor.fetchone()[0] == 0:
        upgrades = [
            ("Catch Rate Boost", "Increases catch success rate for all faction members", 50000, 5, "catch_rate", 0.05),
            ("Shiny Rate Boost", "Increases chance of encountering shiny Veramon", 100000, 3, "shiny_rate", 0.10),
            ("XP Boost", "Increases XP gained from all activities", 75000, 5, "xp_gain", 0.10),
            ("Token Boost", "Increases tokens earned from activities", 60000, 5, "token_gain", 0.10),
            ("Member Capacity", "Increases maximum member capacity", 150000, 3, "member_capacity", 25),
            ("Territory Control", "Allows faction to control more territories", 200000, 3, "territory_capacity", 1),
            ("Daily Token Pool", "Provides daily tokens to distribute among members", 80000, 5, "daily_tokens", 500),
            ("Raid Damage", "Increases damage dealt in faction raids", 90000, 5, "raid_damage", 0.15),
            ("War Power", "Increases points earned in faction wars", 120000, 4, "war_points", 0.15),
            ("Resource Production", "Increases resources gained from territories", 70000, 5, "resource_rate", 0.20)
        ]
        
        for upgrade in upgrades:
            cursor.execute(
                "INSERT INTO faction_upgrades (name, description, cost, max_level, upgrade_type, effect_per_level) VALUES (?, ?, ?, ?, ?, ?)",
                upgrade
            )
    
    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_user_id ON captures(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_captures_active ON captures(user_id, active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_members ON faction_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_upgrades ON faction_purchased_upgrades(faction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_territories ON faction_territories(controlling_faction_id)")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
