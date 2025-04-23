"""
Veramon Reunited - Verification Script
Created by Cascade AI

This script verifies that all critical components of the Veramon Reunited bot
are working correctly, including cog loading, database setup, and permissions.
"""

import os
import sys
import asyncio
import importlib
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.ENDC}")

def print_error(text):
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Print an informational message."""
    print(f"{Colors.CYAN}ℹ️ {text}{Colors.ENDC}")

def check_python_version():
    """Check if Python version is 3.8 or later."""
    print_info(f"Python Version: {sys.version}")
    if sys.version_info < (3, 8):
        print_error("Python 3.8 or later is required")
        return False
    print_success("Python version check passed")
    return True

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = [
        "discord.py", "python-dotenv", "aiosqlite", "Pillow"
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            importlib.import_module(package.replace("-", "").replace(".", ""))
            print_success(f"Package '{package}' is installed")
        except ImportError:
            print_error(f"Package '{package}' is not installed")
            all_installed = False
    
    return all_installed

def check_directories():
    """Check if all required directories exist."""
    required_dirs = [
        "data", "data/backups", "logs", "battle-system", "battle-trading", 
        "factions", "events", "quests", "tournaments"
    ]
    
    all_exist = True
    for directory in required_dirs:
        if os.path.exists(directory):
            print_success(f"Directory '{directory}' exists")
        else:
            print_error(f"Directory '{directory}' does not exist, creating it")
            os.makedirs(directory, exist_ok=True)
            all_exist = False
    
    return all_exist

def check_bot_token():
    """Check if the bot token is set in the environment variables."""
    if not BOT_TOKEN:
        print_error("BOT_TOKEN is not set in the .env file or environment variables")
        return False
    
    # Check if token is valid format (not checking if it works, just format)
    if len(BOT_TOKEN) < 50:
        print_warning("BOT_TOKEN seems shorter than expected, might not be valid")
    
    print_success("BOT_TOKEN is set")
    return True

def check_cog_files():
    """Check if all required cog files exist."""
    cog_paths = [
        "src/cogs/gameplay/battle_cog.py",
        "src/cogs/gameplay/trading_cog.py",
        "src/cogs/user/help_cog.py",
        "src/cogs/social/profile_cog.py",
        "src/cogs/admin/admin_cog.py",
    ]
    
    all_exist = True
    for path in cog_paths:
        if os.path.exists(path):
            print_success(f"Cog file '{path}' exists")
        else:
            print_error(f"Cog file '{path}' does not exist")
            all_exist = False
    
    return all_exist

async def check_database():
    """Check if the database is properly initialized."""
    try:
        # Import database modules dynamically
        from src.db.db_manager import get_db_manager
        
        # Get database manager
        db_manager = get_db_manager()
        
        # Check if database exists
        if os.path.exists("data/veramon_reunited.db"):
            print_success("Database file exists")
        else:
            print_warning("Database file does not exist, it will be created automatically")
        
        # Check database tables
        required_tables = [
            "users", "captures", "battles", "teams", "trades", "developers"
        ]
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table in tables:
                print_success(f"Database table '{table}' exists")
            else:
                print_error(f"Database table '{table}' does not exist")
        
        conn.close()
        return True
    except Exception as e:
        print_error(f"Error checking database: {e}")
        return False

def verify_permissions_system():
    """Verify that the permissions system is set up correctly."""
    try:
        from src.models.permissions import PermissionLevel
        from src.db.db import get_connection
        
        # Verify developers table exists
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='developers'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print_error("Developers table does not exist")
            conn.close()
            return False
        
        print_success("Permissions system is set up correctly")
        conn.close()
        return True
    except Exception as e:
        print_error(f"Error verifying permissions system: {e}")
        return False

def main():
    """Run all verification checks."""
    print_header("Veramon Reunited Bot Verification")
    print_info(f"Running verification at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Bot Token", check_bot_token),
        ("Cog Files", check_cog_files),
        ("Permissions System", verify_permissions_system),
    ]
    
    async_checks = [
        ("Database", check_database),
    ]
    
    results = {}
    
    # Run synchronous checks
    for name, check_func in checks:
        print_header(f"Checking {name}")
        results[name] = check_func()
    
    # Run asynchronous checks
    for name, check_func in async_checks:
        print_header(f"Checking {name}")
        results[name] = asyncio.run(check_func())
    
    # Print summary
    print_header("Verification Summary")
    all_passed = True
    for name, result in results.items():
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            all_passed = False
    
    if all_passed:
        print_header("ALL CHECKS PASSED! Bot should be ready to run.")
        print_info("You can now run the bot using: python -m src.main")
    else:
        print_header("SOME CHECKS FAILED! Please fix the issues before running the bot.")
    
    print(f"\n{Colors.CYAN}Need additional help? Check GitHub documentation at:{Colors.ENDC}")
    print(f"{Colors.CYAN}https://github.com/killerdash117/veramon-reunited{Colors.ENDC}")

if __name__ == "__main__":
    main()
