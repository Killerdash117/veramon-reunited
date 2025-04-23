import os
import sqlite3
import threading
from typing import Dict, Union, Optional
from queue import Queue, Empty
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "veramon.db")

# Connection pool settings
MAX_CONNECTIONS = 10
TIMEOUT = 5.0  # seconds to wait for a connection before timeout
_connection_pool = Queue(maxsize=MAX_CONNECTIONS)
_pool_lock = threading.RLock()
_active_connections = 0

class PooledConnection:
    """A wrapper for SQLite connections that returns them to the pool when closed."""
    
    def __init__(self, connection):
        self.connection = connection
        self.closed = False
        
    def cursor(self):
        """Get a cursor from the connection."""
        if self.closed:
            raise sqlite3.Error("Connection has been closed")
        return self.connection.cursor()
        
    def commit(self):
        """Commit changes to the database."""
        if self.closed:
            raise sqlite3.Error("Connection has been closed")
        return self.connection.commit()
        
    def rollback(self):
        """Rollback changes to the database."""
        if self.closed:
            raise sqlite3.Error("Connection has been closed")
        return self.connection.rollback()
        
    def close(self):
        """Return the connection to the pool instead of closing it."""
        if not self.closed:
            self.closed = True
            return_connection_to_pool(self.connection)
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

def _create_connection():
    """Create a new SQLite connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_pool():
    """Initialize the connection pool."""
    global _active_connections
    
    with _pool_lock:
        # Clear any existing connections
        while not _connection_pool.empty():
            try:
                conn = _connection_pool.get_nowait()
                conn.close()
            except Empty:
                break
                
        # Create initial connections
        for _ in range(MAX_CONNECTIONS // 2):  # Start with half capacity
            connection = _create_connection()
            _connection_pool.put(connection)
            _active_connections += 1

def get_connection(timeout: float = 5.0) -> PooledConnection:
    """
    Get a connection from the pool or create a new one if needed.
    
    Args:
        timeout: Timeout in seconds for database operations (default: 5.0)
        
    Returns:
        A pooled database connection.
    
    Raises:
        sqlite3.Error: If the connection pool is exhausted and no new connections can be created.
    """
    global _active_connections
    
    # Initialize pool if needed
    if _connection_pool.empty() and _active_connections == 0:
        initialize_pool()
    
    # Try to get a connection from the pool
    try:
        connection = _connection_pool.get(block=True, timeout=timeout)
        return PooledConnection(connection)
    except Empty:
        # If pool is empty but we can create more connections
        with _pool_lock:
            if _active_connections < MAX_CONNECTIONS:
                connection = _create_connection()
                _active_connections += 1
                return PooledConnection(connection)
            else:
                # No available connections and at max capacity
                raise sqlite3.Error("Connection pool exhausted, try again later")

def return_connection_to_pool(connection):
    """Return a connection to the pool."""
    # Check if connection is healthy before returning to pool
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        _connection_pool.put(connection)
    except sqlite3.Error:
        # If connection is bad, close it and create a new one
        try:
            connection.close()
        except:
            pass
            
        with _pool_lock:
            global _active_connections
            _active_connections -= 1
            
            # Create a replacement connection if below minimum threshold
            if _active_connections < MAX_CONNECTIONS // 2:
                new_connection = _create_connection()
                _connection_pool.put(new_connection)
                _active_connections += 1

def close_all_connections():
    """Close all connections in the pool."""
    with _pool_lock:
        global _active_connections
        
        # Empty the pool and close all connections
        while not _connection_pool.empty():
            try:
                conn = _connection_pool.get_nowait()
                conn.close()
            except Empty:
                break
                
        _active_connections = 0

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
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # Faction activity log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_activity (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        user_id TEXT,
        activity_type TEXT NOT NULL,
        activity_data TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # Faction upgrades - permanent faction improvements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_upgrades (
        upgrade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        upgrade_type TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        effect_data TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE
    )
    """)
    
    # Faction buffs - temporary faction-wide effects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_buffs (
        buff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER NOT NULL,
        buff_type TEXT NOT NULL,
        strength INTEGER NOT NULL,
        start_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time TEXT NOT NULL,
        applied_by TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE CASCADE,
        FOREIGN KEY (applied_by) REFERENCES users(user_id)
    )
    """)
    
    # Faction territories - locations controlled by factions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_territories (
        territory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        faction_id INTEGER,
        name TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        capture_time TEXT,
        contested BOOLEAN DEFAULT 0,
        location_data TEXT NOT NULL,
        FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE SET NULL
    )
    """)
    
    # Faction wars - track faction vs faction conflicts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_wars (
        war_id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER NOT NULL,
        defender_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        start_time TEXT,
        end_time TEXT,
        territory_id INTEGER,
        score_attacker INTEGER DEFAULT 0,
        score_defender INTEGER DEFAULT 0,
        FOREIGN KEY (attacker_id) REFERENCES factions(faction_id),
        FOREIGN KEY (defender_id) REFERENCES factions(faction_id),
        FOREIGN KEY (territory_id) REFERENCES faction_territories(territory_id)
    )
    """)
    
    # Faction war participation - track individual contributions to wars
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faction_war_participants (
        war_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        participation_type TEXT NOT NULL,
        contribution_points INTEGER DEFAULT 0,
        joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (war_id, user_id),
        FOREIGN KEY (war_id) REFERENCES faction_wars(war_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    # Create indices for faction-related tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_members ON faction_members(faction_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_activity ON faction_activity(faction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_upgrades ON faction_upgrades(faction_id, upgrade_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_buffs ON faction_buffs(faction_id, buff_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_territories ON faction_territories(faction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faction_wars ON faction_wars(attacker_id, defender_id)")
    
    # Trades system
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        initiator_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (initiator_id) REFERENCES users(user_id),
        FOREIGN KEY (recipient_id) REFERENCES users(user_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_items (
        trade_id INTEGER NOT NULL,
        item_type TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        owner_id TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (trade_id, item_type, item_id, owner_id),
        FOREIGN KEY (trade_id) REFERENCES trades(trade_id) ON DELETE CASCADE,
        FOREIGN KEY (owner_id) REFERENCES users(user_id)
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_users ON trades(initiator_id, recipient_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_items ON trade_items(trade_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_owner ON trade_items(owner_id)")
    
    # Enhanced Battle System Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battles (
        battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_type TEXT NOT NULL,  -- 'pvp', 'pve', 'multi'
        status TEXT NOT NULL,       -- 'waiting', 'active', 'completed', 'cancelled'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        winner_id TEXT,             -- ID of winning player or team
        battle_data TEXT,           -- JSON data of battle state
        expiry_time TEXT            -- When battle invitation expires
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_participants (
        battle_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        team_id INTEGER DEFAULT 0,
        is_host BOOLEAN DEFAULT 0,
        is_npc BOOLEAN DEFAULT 0,
        status TEXT NOT NULL,       -- 'invited', 'joined', 'declined', 'left'
        joined_at TEXT,
        PRIMARY KEY (battle_id, user_id),
        FOREIGN KEY (battle_id) REFERENCES battles(battle_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_teams (
        battle_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        team_name TEXT,
        team_color TEXT,
        PRIMARY KEY (battle_id, team_id),
        FOREIGN KEY (battle_id) REFERENCES battles(battle_id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_veramon (
        battle_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        capture_id INTEGER NOT NULL,
        slot_position INTEGER NOT NULL,
        current_hp INTEGER NOT NULL,
        status_effects TEXT,        -- JSON array of status effects
        stat_stages TEXT,           -- JSON object of stat modifications
        active BOOLEAN DEFAULT 0,
        PRIMARY KEY (battle_id, user_id, capture_id),
        FOREIGN KEY (battle_id) REFERENCES battles(battle_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (capture_id) REFERENCES captures(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        action_type TEXT NOT NULL,  -- 'move', 'switch', 'item', 'flee'
        actor_id TEXT NOT NULL,     -- User who performed the action
        target_ids TEXT,            -- JSON array of target IDs
        action_data TEXT,           -- JSON data of action details
        result_data TEXT,           -- JSON data of action result
        FOREIGN KEY (battle_id) REFERENCES battles(battle_id) ON DELETE CASCADE
    )
    """)
    
    # Updated NPC trainers table to match admin_battle_system.py expectations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npc_trainers (
        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        difficulty TEXT NOT NULL,   -- 'easy', 'normal', 'hard', 'expert', 'champion'
        theme TEXT DEFAULT 'mixed', -- Type specialization of the trainer
        veramon_count INTEGER DEFAULT 3,
        min_level INTEGER DEFAULT 5,
        max_level INTEGER DEFAULT 15,
        token_reward INTEGER DEFAULT 25,
        experience_reward INTEGER DEFAULT 300,
        avatar_url TEXT,
        description TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Add NPC trainer teams table for specific Veramon compositions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npc_trainer_teams (
        team_id INTEGER PRIMARY KEY AUTOINCREMENT,
        trainer_id INTEGER NOT NULL,
        veramon_name TEXT NOT NULL,
        level INTEGER NOT NULL,
        position INTEGER NOT NULL,   -- Position in team (1-6)
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trainer_id) REFERENCES npc_trainers(trainer_id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_status ON battles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_participants ON battle_participants(battle_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_veramon ON battle_veramon(battle_id, user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_logs ON battle_logs(battle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_npc_trainers ON npc_trainers(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_npc_trainer_teams ON npc_trainer_teams(trainer_id, position)")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
