import os
import sqlite3
from datetime import datetime

def update_database():
    """
    Schema update for v0.31.002 - Evolution Paths, Forms, and Weather System.
    
    This update adds database support for the following features:
    1. Special forms for Veramon (via active_form column)
    2. Dynamic weather system in biomes
    3. Special exploration areas unlocked via achievements
    4. Form discovery tracking
    5. Evolution history tracking
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    
    # Get database path
    db_path = os.path.join('data', 'veramon.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add active_form column to captures table
        cursor.execute("PRAGMA table_info(captures)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'active_form' not in columns:
            cursor.execute("ALTER TABLE captures ADD COLUMN active_form TEXT")
            print("Added active_form column to captures table")
        else:
            print("Column active_form already exists in captures table")
            
        # 2. Create biome_weather table for tracking current weather
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS biome_weather (
            biome_id TEXT PRIMARY KEY,
            current_weather TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            next_change TIMESTAMP,
            weather_history TEXT
        )
        """)
        print("Created or verified biome_weather table")
        
        # 3. Create special_area_access table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS special_area_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            biome_id TEXT NOT NULL,
            special_area_id TEXT NOT NULL,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, biome_id, special_area_id)
        )
        """)
        print("Created or verified special_area_access table")
        
        # 4. Add accessed_forms column to user_data
        cursor.execute("PRAGMA table_info(user_data)")
        user_data_columns = [info[1] for info in cursor.fetchall()]
        
        if 'accessed_forms' not in user_data_columns:
            # First check if user_data table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_data'")
            if cursor.fetchone():
                cursor.execute("ALTER TABLE user_data ADD COLUMN accessed_forms TEXT DEFAULT '[]'")
                print("Added accessed_forms column to user_data table")
            else:
                # Create user_data table if it doesn't exist
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id TEXT PRIMARY KEY,
                    tokens INTEGER DEFAULT 0,
                    caught_veramon TEXT DEFAULT '[]',
                    accessed_forms TEXT DEFAULT '[]'
                )
                """)
                print("Created user_data table with accessed_forms column")
        else:
            print("Column accessed_forms already exists in user_data table")
            
        # 5. Create evolution_history table to track evolution choices
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            capture_id INTEGER NOT NULL,
            original_form TEXT,
            new_form TEXT,
            evolution_path TEXT,
            evolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (capture_id) REFERENCES captures(id)
        )
        """)
        print("Created or verified evolution_history table")
        
        # Create indices for better query performance
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_special_area_access_user_id ON special_area_access(user_id)
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evolution_history_user_id ON evolution_history(user_id)
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evolution_history_capture_id ON evolution_history(capture_id)
        """)
        
        print("Created indices for better query performance")
        
        # Add timestamp for update tracking
        update_time = datetime.utcnow().isoformat()
        
        # Check if schema_versions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_versions'")
        if not cursor.fetchone():
            # Create schema_versions table
            cursor.execute("""
            CREATE TABLE schema_versions (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """)
            print("Created schema_versions table")
            
        # Record this update in schema_versions
        cursor.execute("""
        INSERT OR REPLACE INTO schema_versions (version, applied_at, description)
        VALUES (?, ?, ?)
        """, ('v0.31.002', update_time, 'Evolution Paths, Forms, and Weather System'))
        print("Recorded schema update in version history")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"Successfully completed schema update v0.31.002 at {update_time}")
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    update_database()
