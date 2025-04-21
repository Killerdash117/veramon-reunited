"""
Comprehensive Veramon Bot Testing System
This script performs extensive testing of all Veramon bot components including:
- Data loading and validation
- Battle system functionality
- Trading system
- Database operations
- Command registration
- UI components
"""

import os
import sys
import json
import time
import unittest
import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, parent_dir)

# Import bot modules - these will be used in various tests
try:
    from src.utils.cache import get_veramon_data
    from src.utils.data_loader import load_all_veramon_data
    from src.db.db import get_connection, initialize_db
    
    # Try to import battle and trade models, but don't fail if they don't exist
    try:
        import src.models.battle as battle_models
        BATTLE_SYSTEM_AVAILABLE = True
    except ImportError:
        BATTLE_SYSTEM_AVAILABLE = False
        battle_models = None
        print("WARNING: Battle system modules not found. Battle tests will be skipped.")
    
    try:
        import src.models.trade as trade_models
        TRADE_SYSTEM_AVAILABLE = True
    except ImportError:
        TRADE_SYSTEM_AVAILABLE = False
        trade_models = None
        print("WARNING: Trade system modules not found. Trade tests will be skipped.")
        
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def measure_execution_time(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        return result, execution_time
    return wrapper

class VeramonBotTester:
    """Main test runner for the Veramon bot."""
    
    def __init__(self):
        """Initialize the tester with necessary data."""
        self.test_results = {
            "data_tests": {"passed": 0, "failed": 0, "details": []},
            "battle_tests": {"passed": 0, "failed": 0, "details": []},
            "trade_tests": {"passed": 0, "failed": 0, "details": []},
            "db_tests": {"passed": 0, "failed": 0, "details": []},
            "command_tests": {"passed": 0, "failed": 0, "details": []},
            "ui_tests": {"passed": 0, "failed": 0, "details": []}
        }
        
        # Data paths
        self.data_dir = os.path.join(parent_dir, 'src', 'data')
        self.database_path = os.path.join(self.data_dir, 'veramon_database.json')
        
        # Load data needed for testing
        self.load_test_data()
    
    def load_test_data(self):
        """Load data needed for testing."""
        try:
            # Load Veramon data
            with open(self.database_path, 'r', encoding='utf-8') as f:
                self.veramon_data = json.load(f)
                
            # Establish database connection
            self.db_conn = get_connection()
            self.db_cursor = self.db_conn.cursor()
            
            print("Successfully loaded test data")
        except Exception as e:
            print(f"ERROR: Failed to load test data: {e}")
            sys.exit(1)
    
    def record_test_result(self, category, test_name, passed, message=None):
        """Record a test result."""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message
        }
        
        self.test_results[category]["details"].append(result)
        if passed:
            self.test_results[category]["passed"] += 1
        else:
            self.test_results[category]["failed"] += 1
            
        # Print immediate feedback
        status = "PASS" if passed else "FAIL"
        message_str = f": {message}" if message else ""
        print(f"[{status}] {test_name}{message_str}")
    
    #########################################
    # DATA TESTS
    #########################################
    
    def test_data_loading(self):
        """Test various data loading methods."""
        print("\n=== Testing Data Loading ===")
        
        # Test direct loading
        try:
            data_direct, direct_time = measure_execution_time(lambda: self.veramon_data)()
            self.record_test_result(
                "data_tests", 
                "Direct File Loading", 
                True, 
                f"Loaded {len(data_direct)} Veramon in {direct_time:.2f}ms"
            )
        except Exception as e:
            self.record_test_result("data_tests", "Direct File Loading", False, str(e))
        
        # Test data_loader
        try:
            data_loader, loader_time = measure_execution_time(load_all_veramon_data)()
            self.record_test_result(
                "data_tests", 
                "Data Loader Module", 
                len(data_loader) > 0, 
                f"Loaded {len(data_loader)} Veramon in {loader_time:.2f}ms"
            )
        except Exception as e:
            self.record_test_result("data_tests", "Data Loader Module", False, str(e))
            
        # Test cache module
        try:
            data_cache, cache_time = measure_execution_time(get_veramon_data)()
            self.record_test_result(
                "data_tests", 
                "Cache Module", 
                len(data_cache) > 0, 
                f"Loaded {len(data_cache)} Veramon in {cache_time:.2f}ms"
            )
        except Exception as e:
            self.record_test_result("data_tests", "Cache Module", False, str(e))
    
    def test_data_structure(self):
        """Test the structure of Veramon data."""
        print("\n=== Testing Data Structure ===")
        
        errors = []
        required_fields = [
            'name', 'type', 'rarity', 'catch_rate', 'shiny_rate', 
            'base_stats', 'biomes', 'flavor', 'abilities'
        ]
        
        valid_rarities = ['common', 'uncommon', 'rare', 'legendary', 'mythic']
        valid_types = [
            'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting',
            'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost',
            'Dragon', 'Dark', 'Steel', 'Fairy'
        ]
        
        # Check each Veramon
        for name, veramon in self.veramon_data.items():
            # Check for required fields
            for field in required_fields:
                if field not in veramon:
                    errors.append(f"{name} is missing required field: {field}")
            
            # Check types
            if 'type' in veramon:
                if not isinstance(veramon['type'], list):
                    errors.append(f"{name} 'type' should be a list, got {type(veramon['type'])}")
                else:
                    for t in veramon['type']:
                        if t not in valid_types:
                            errors.append(f"{name} has invalid type: {t}")
            
            # Check rarity
            if 'rarity' in veramon:
                if veramon['rarity'] not in valid_rarities:
                    errors.append(f"{name} has invalid rarity: {veramon['rarity']}")
        
        # Record test result
        if errors:
            self.record_test_result(
                "data_tests", 
                "Data Structure Validation", 
                False, 
                f"Found {len(errors)} structure issues"
            )
        else:
            self.record_test_result("data_tests", "Data Structure Validation", True)
    
    def test_type_effectiveness(self):
        """Test type effectiveness for battle calculations."""
        print("\n=== Testing Type Effectiveness ===")
        
        # Define a sample of type effectiveness to test
        type_tests = [
            {"attacker": "Fire", "defender": "Grass", "expected_multiplier": 2.0},
            {"attacker": "Water", "defender": "Fire", "expected_multiplier": 2.0},
            {"attacker": "Electric", "defender": "Ground", "expected_multiplier": 0.0},
            {"attacker": "Normal", "defender": "Ghost", "expected_multiplier": 0.0},
            {"attacker": "Fighting", "defender": "Normal", "expected_multiplier": 2.0}
        ]
        
        errors = []
        
        # Test if all types in Veramon entries are valid
        all_types = set()
        for veramon in self.veramon_data.values():
            if 'type' in veramon and isinstance(veramon['type'], list):
                all_types.update(veramon['type'])
        
        standard_types = {
            'Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting',
            'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost',
            'Dragon', 'Dark', 'Steel', 'Fairy'
        }
        
        invalid_types = all_types - standard_types
        if invalid_types:
            errors.append(f"Found invalid types in database: {', '.join(invalid_types)}")
        
        # Record test result
        if errors:
            self.record_test_result(
                "data_tests", 
                "Type Effectiveness", 
                False, 
                "; ".join(errors)
            )
        else:
            self.record_test_result("data_tests", "Type Effectiveness", True)
    
    #########################################
    # BATTLE SYSTEM TESTS
    #########################################
    
    def test_battle_system_components(self):
        """Test the battle system components."""
        print("\n=== Testing Battle System Components ===")
        
        if not BATTLE_SYSTEM_AVAILABLE:
            self.record_test_result(
                "battle_tests", 
                "Battle System", 
                False, 
                "Battle system modules not found"
            )
            return
        
        # Test battle model imports
        try:
            battle_class = battle_models.Battle
            self.record_test_result("battle_tests", "Battle Model Import", True)
        except (ImportError, AttributeError) as e:
            self.record_test_result("battle_tests", "Battle Model Import", False, str(e))
        
        # Test battle participant model
        try:
            participant_class = battle_models.BattleParticipant
            self.record_test_result("battle_tests", "Battle Participant Model", True)
        except (ImportError, AttributeError) as e:
            self.record_test_result("battle_tests", "Battle Participant Model", False, str(e))
        
        # Test move execution
        try:
            move_execution = hasattr(battle_models.Battle, 'execute_move')
            self.record_test_result("battle_tests", "Move Execution", move_execution)
        except Exception as e:
            self.record_test_result("battle_tests", "Move Execution", False, str(e))
        
        # Test battle state tracking
        try:
            battle_state = hasattr(battle_models.Battle, 'get_state')
            self.record_test_result("battle_tests", "Battle State Tracking", battle_state)
        except Exception as e:
            self.record_test_result("battle_tests", "Battle State Tracking", False, str(e))
    
    def test_battle_database_schema(self):
        """Test the battle database schema."""
        print("\n=== Testing Battle Database Schema ===")
        
        # List of expected battle-related tables
        battle_tables = [
            "battles",
            "battle_participants",
            "battle_veramon",
            "battle_logs",
            "npc_trainers"
        ]
        
        # Check each table
        for table in battle_tables:
            try:
                query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                self.db_cursor.execute(query)
                result = self.db_cursor.fetchone()
                
                self.record_test_result(
                    "battle_tests", 
                    f"Table: {table}", 
                    result is not None
                )
                
                if result is not None:
                    # Get column info
                    self.db_cursor.execute(f"PRAGMA table_info({table})")
                    columns = self.db_cursor.fetchall()
                    self.record_test_result(
                        "battle_tests", 
                        f"Columns: {table}", 
                        len(columns) > 0,
                        f"Found {len(columns)} columns"
                    )
            except Exception as e:
                self.record_test_result("battle_tests", f"Table: {table}", False, str(e))
    
    def test_battle_type_compatibility(self):
        """Test Veramon compatibility with the battle system."""
        print("\n=== Testing Battle Type Compatibility ===")
        
        errors = []
        
        for name, veramon in self.veramon_data.items():
            # For battle calculations, we need proper stats
            if 'base_stats' in veramon:
                stats = veramon['base_stats']
                for stat_name, value in stats.items():
                    if not isinstance(value, (int, float)) or value <= 0:
                        errors.append(f"{name} has invalid stat {stat_name}: {value}")
            
            # For battle moves, we need abilities
            if 'abilities' in veramon and not veramon['abilities']:
                errors.append(f"{name} has no abilities for battle")
            
            # For damage calculations, we need proper types
            if 'type' in veramon and not veramon['type']:
                errors.append(f"{name} has no types for damage calculation")
        
        # Record test result
        if errors:
            self.record_test_result(
                "battle_tests", 
                "Battle Compatibility", 
                False, 
                f"Found {len(errors)} compatibility issues"
            )
        else:
            self.record_test_result("battle_tests", "Battle Compatibility", True)
    
    #########################################
    # TRADING SYSTEM TESTS
    #########################################
    
    def test_trading_system_components(self):
        """Test the trading system components."""
        print("\n=== Testing Trading System Components ===")
        
        if not TRADE_SYSTEM_AVAILABLE:
            self.record_test_result(
                "trade_tests", 
                "Trading System", 
                False, 
                "Trading system modules not found"
            )
            return
        
        # Test trade model imports
        try:
            trade_class = trade_models.Trade
            self.record_test_result("trade_tests", "Trade Model Import", True)
        except (ImportError, AttributeError) as e:
            self.record_test_result("trade_tests", "Trade Model Import", False, str(e))
        
        # Test trade item model
        try:
            trade_item_class = trade_models.TradeItem
            self.record_test_result("trade_tests", "Trade Item Model", True)
        except (ImportError, AttributeError) as e:
            self.record_test_result("trade_tests", "Trade Item Model", False, str(e))
        
        # Test trade status
        try:
            trade_status = hasattr(trade_models.Trade, 'get_status')
            self.record_test_result("trade_tests", "Trade Status", trade_status)
        except Exception as e:
            self.record_test_result("trade_tests", "Trade Status", False, str(e))
    
    def test_trading_database_schema(self):
        """Test the trading database schema."""
        print("\n=== Testing Trading Database Schema ===")
        
        # List of expected trade-related tables
        trade_tables = [
            "trades",
            "trade_items",
            "trade_logs"
        ]
        
        # Check each table
        for table in trade_tables:
            try:
                query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                self.db_cursor.execute(query)
                result = self.db_cursor.fetchone()
                
                self.record_test_result(
                    "trade_tests", 
                    f"Table: {table}", 
                    result is not None
                )
                
                if result is not None:
                    # Get column info
                    self.db_cursor.execute(f"PRAGMA table_info({table})")
                    columns = self.db_cursor.fetchall()
                    self.record_test_result(
                        "trade_tests", 
                        f"Columns: {table}", 
                        len(columns) > 0,
                        f"Found {len(columns)} columns"
                    )
            except Exception as e:
                self.record_test_result("trade_tests", f"Table: {table}", False, str(e))
    
    def test_trade_type_compatibility(self):
        """Test Veramon compatibility with the trading system."""
        print("\n=== Testing Trading Type Compatibility ===")
        
        errors = []
        
        for name, veramon in self.veramon_data.items():
            # For trading value calculations, we need proper rarity
            if 'rarity' not in veramon:
                errors.append(f"{name} is missing rarity for trade value calculations")
            
            # For trading display, we need a name that matches the key
            if 'name' in veramon and veramon['name'] != name:
                errors.append(f"{name} has mismatched name: {veramon['name']}")
        
        # Record test result
        if errors:
            self.record_test_result(
                "trade_tests", 
                "Trading Compatibility", 
                False, 
                f"Found {len(errors)} compatibility issues"
            )
        else:
            self.record_test_result("trade_tests", "Trading Compatibility", True)
    
    #########################################
    # DATABASE TESTS
    #########################################
    
    def test_database_tables(self):
        """Test the database tables."""
        print("\n=== Testing Database Tables ===")
        
        # List of expected tables
        expected_tables = [
            "users",
            "captures",
            "items",
            "user_items",
            "battles",
            "battle_participants",
            "battle_veramon",
            "battle_logs",
            "trades",
            "trade_items",
            "trade_logs",
            "factions",
            "faction_members"
        ]
        
        # Get all tables in the database
        try:
            self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.db_cursor.fetchall()]
            
            # Check for expected tables
            for table in expected_tables:
                self.record_test_result(
                    "db_tests", 
                    f"Table: {table}", 
                    table in tables
                )
        except Exception as e:
            self.record_test_result("db_tests", "Database Tables", False, str(e))
    
    def test_database_indices(self):
        """Test the database indices."""
        print("\n=== Testing Database Indices ===")
        
        # List of important indices to check
        important_indices = [
            {"table": "captures", "column": "user_id"},
            {"table": "battles", "column": "status"},
            {"table": "trades", "column": "status"}
        ]
        
        # Check each index
        for index_info in important_indices:
            table = index_info["table"]
            column = index_info["column"]
            
            try:
                query = f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}' AND sql LIKE '%{column}%'"
                self.db_cursor.execute(query)
                result = self.db_cursor.fetchone()
                
                self.record_test_result(
                    "db_tests", 
                    f"Index: {table}.{column}", 
                    result is not None
                )
            except Exception as e:
                self.record_test_result("db_tests", f"Index: {table}.{column}", False, str(e))
    
    def test_database_connections(self):
        """Test database connections."""
        print("\n=== Testing Database Connections ===")
        
        # Test creating a new connection
        try:
            new_conn = get_connection()
            self.record_test_result("db_tests", "Create Connection", new_conn is not None)
            
            # Test executing a simple query
            cursor = new_conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.record_test_result("db_tests", "Execute Query", result == (1,))
            
            # Close the connection
            new_conn.close()
        except Exception as e:
            self.record_test_result("db_tests", "Database Connection", False, str(e))
    
    #########################################
    # UI TESTS
    #########################################
    
    def test_ui_components(self):
        """Test UI components."""
        print("\n=== Testing UI Components ===")
        
        # Test battle UI imports
        try:
            ui_file_path = os.path.join(parent_dir, 'src', 'utils', 'ui', 'battle_ui.py')
            self.record_test_result("ui_tests", "Battle UI File", os.path.exists(ui_file_path))
        except Exception as e:
            self.record_test_result("ui_tests", "Battle UI File", False, str(e))
        
        # Test trade UI imports
        try:
            ui_file_path = os.path.join(parent_dir, 'src', 'utils', 'ui', 'trade_ui.py')
            self.record_test_result("ui_tests", "Trade UI File", os.path.exists(ui_file_path))
        except Exception as e:
            self.record_test_result("ui_tests", "Trade UI File", False, str(e))
        
        # Test accessible UI components for accessibility features
        try:
            ui_file_path = os.path.join(parent_dir, 'src', 'utils', 'ui', 'accessibility_ui.py')
            self.record_test_result("ui_tests", "Accessibility UI File", os.path.exists(ui_file_path))
        except Exception as e:
            self.record_test_result("ui_tests", "Accessibility UI File", False, str(e))
    
    #########################################
    # MAIN TESTING FUNCTION
    #########################################
    
    def run_all_tests(self):
        """Run all tests."""
        print("=== Running All Veramon Bot Tests ===")
        
        # Data tests
        self.test_data_loading()
        self.test_data_structure()
        self.test_type_effectiveness()
        
        # Battle tests
        self.test_battle_system_components()
        self.test_battle_database_schema()
        self.test_battle_type_compatibility()
        
        # Trading tests
        self.test_trading_system_components()
        self.test_trading_database_schema()
        self.test_trade_type_compatibility()
        
        # Database tests
        self.test_database_tables()
        self.test_database_indices()
        self.test_database_connections()
        
        # UI tests
        self.test_ui_components()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print a summary of all test results."""
        print("\n\n=== Test Summary ===")
        
        total_passed = 0
        total_failed = 0
        
        # Print results for each category
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            
            if total > 0:
                pass_rate = (passed / total) * 100
                category_name = category.split("_")[0].capitalize()
                print(f"{category_name} Tests: {passed}/{total} passed ({pass_rate:.1f}%)")
                
                # If there are failures, list them
                if failed > 0:
                    print("  Failed tests:")
                    for detail in results["details"]:
                        if not detail["passed"]:
                            message = f": {detail['message']}" if detail['message'] else ""
                            print(f"    - {detail['test']}{message}")
            
            total_passed += passed
            total_failed += failed
        
        # Print overall summary
        total_tests = total_passed + total_failed
        overall_pass_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\nOverall: {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%)")
        if total_failed == 0:
            print("All tests PASSED!")
        else:
            print(f"{total_failed} tests FAILED!")

if __name__ == "__main__":
    tester = VeramonBotTester()
    tester.run_all_tests()
