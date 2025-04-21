"""
Comprehensive Veramon Bot Testing Framework
------------------------------------------
This script provides a complete test suite for all aspects of the Veramon bot:
1. Data Structure and Integrity
2. Database Schema and Connections
3. Battle System Functionality 
4. Trading System Integration
5. UI Components
6. Command Registration
"""

import os
import sys
import json
import time
import unittest
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("veramon_test")

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, parent_dir)

# Import bot modules
try:
    # Core data modules
    from src.utils.cache import get_veramon_data
    from src.utils.data_loader import load_all_veramon_data
    from src.db.db import get_connection, initialize_db
    
    # Try to import optional modules without failing
    HAS_BATTLE_SYSTEM = False
    HAS_TRADE_SYSTEM = False
    
    try:
        from src.models.battle import Battle, BattleType, BattleStatus
        from src.models.battle_mechanics import calculate_damage
        HAS_BATTLE_SYSTEM = True
    except ImportError as e:
        logger.warning(f"Battle system import failed: {e}")
    
    try:
        # If trade.py doesn't exist, this will fail silently
        import importlib.util
        trade_spec = importlib.util.find_spec('src.models.trade')
        if trade_spec:
            from src.models.trade import Trade
            HAS_TRADE_SYSTEM = True
    except ImportError as e:
        logger.warning(f"Trade system import failed: {e}")
    
except ImportError as e:
    logger.error(f"Failed to import critical modules: {e}")
    sys.exit(1)

class TestResult:
    """Simple class to track test results."""
    def __init__(self, name, category):
        self.name = name
        self.category = category
        self.passed = False
        self.message = None
        self.execution_time = 0
    
    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        message = f": {self.message}" if self.message else ""
        return f"[{status}] {self.name}{message}"

class VeramonTestSuite:
    """Comprehensive test suite for the Veramon bot."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.results = []
        self.categories = {
            "data": "Data Structure Tests",
            "database": "Database Tests",
            "battle": "Battle System Tests",
            "trading": "Trading System Tests",
            "commands": "Command Tests",
            "ui": "UI Component Tests"
        }
        
        # Set up testing environment
        self.setup()
    
    def setup(self):
        """Set up the testing environment."""
        # Data paths
        self.data_dir = os.path.join(parent_dir, 'src', 'data')
        self.database_path = os.path.join(self.data_dir, 'veramon_database.json')
        
        # Load reference data
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                self.veramon_data = json.load(f)
            logger.info(f"Loaded {len(self.veramon_data)} Veramon entries")
            
            # Set up database connection
            self.db_conn = get_connection()
            self.db_cursor = self.db_conn.cursor()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to set up testing environment: {e}")
            sys.exit(1)
    
    def record_result(self, name, category, passed, message=None, execution_time=0):
        """Record a test result."""
        result = TestResult(name, category)
        result.passed = passed
        result.message = message
        result.execution_time = execution_time
        
        self.results.append(result)
        
        # Print immediate feedback
        logger.info(str(result))
    
    def time_execution(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        return result, execution_time
    
    #----------------------------------------------------------------------
    # DATA STRUCTURE TESTS
    #----------------------------------------------------------------------
    
    def test_data_loading(self):
        """Test data loading capabilities."""
        logger.info("=== Testing Data Loading ===")
        
        # Test direct loading
        direct_data, direct_time = self.time_execution(lambda: self.veramon_data)
        self.record_result(
            "Direct File Loading", 
            "data", 
            len(direct_data) > 0, 
            f"Loaded {len(direct_data)} Veramon in {direct_time:.2f}ms",
            direct_time
        )
        
        # Test data loader module
        try:
            loader_data, loader_time = self.time_execution(load_all_veramon_data)
            self.record_result(
                "Data Loader Module", 
                "data", 
                len(loader_data) > 0, 
                f"Loaded {len(loader_data)} Veramon in {loader_time:.2f}ms",
                loader_time
            )
        except Exception as e:
            self.record_result("Data Loader Module", "data", False, str(e))
        
        # Test cache module
        try:
            cache_data, cache_time = self.time_execution(get_veramon_data)
            self.record_result(
                "Cache Module", 
                "data", 
                len(cache_data) > 0, 
                f"Loaded {len(cache_data)} Veramon in {cache_time:.2f}ms",
                cache_time
            )
        except Exception as e:
            self.record_result("Cache Module", "data", False, str(e))
        
        # Test data consistency
        if 'loader_data' in locals() and 'cache_data' in locals():
            match_direct_loader = len(direct_data) == len(loader_data)
            match_loader_cache = len(loader_data) == len(cache_data)
            
            self.record_result(
                "Data Consistency", 
                "data", 
                match_direct_loader and match_loader_cache,
                f"Found {len(direct_data)} entries in all loading methods"
            )
    
    def test_veramon_structure(self):
        """Test the structure of Veramon entries."""
        logger.info("=== Testing Veramon Structure ===")
        
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
        
        # Test structure of each Veramon
        for name, veramon in self.veramon_data.items():
            # Check for required fields
            for field in required_fields:
                if field not in veramon:
                    errors.append(f"{name} missing field: {field}")
            
            # Check type field
            if 'type' in veramon:
                if not isinstance(veramon['type'], list):
                    errors.append(f"{name} has invalid type format: {veramon['type']}")
                else:
                    for t in veramon['type']:
                        if t not in valid_types:
                            errors.append(f"{name} has invalid type: {t}")
            
            # Check rarity field
            if 'rarity' in veramon and veramon['rarity'] not in valid_rarities:
                errors.append(f"{name} has invalid rarity: {veramon['rarity']}")
            
            # Check abilities format
            if 'abilities' in veramon and not isinstance(veramon['abilities'], dict):
                errors.append(f"{name} has invalid abilities format")
            
            # Check base stats
            if 'base_stats' in veramon:
                required_stats = ['hp', 'attack', 'defense', 'speed']
                for stat in required_stats:
                    if stat not in veramon['base_stats']:
                        errors.append(f"{name} missing base stat: {stat}")
                    elif not isinstance(veramon['base_stats'][stat], (int, float)):
                        errors.append(f"{name} has invalid {stat} value: {veramon['base_stats'][stat]}")
        
        # Record test result
        self.record_result(
            "Veramon Structure", 
            "data", 
            len(errors) == 0, 
            f"Found {len(errors)} structure issues" if errors else "All entries valid"
        )
    
    def test_evolution_chains(self):
        """Test evolution chain validity."""
        logger.info("=== Testing Evolution Chains ===")
        
        errors = []
        
        # Check all evolution references
        for name, veramon in self.veramon_data.items():
            if 'evolution' in veramon and veramon['evolution']:
                if isinstance(veramon['evolution'], dict):
                    for evo_name in veramon['evolution'].values():
                        if evo_name not in self.veramon_data:
                            errors.append(f"{name} has invalid evolution reference: {evo_name}")
                elif isinstance(veramon['evolution'], list):
                    for evo in veramon['evolution']:
                        if 'evolves_to' in evo and evo['evolves_to'] not in self.veramon_data:
                            errors.append(f"{name} has invalid evolution reference: {evo['evolves_to']}")
        
        # Record test result
        self.record_result(
            "Evolution Chains", 
            "data", 
            len(errors) == 0, 
            f"Found {len(errors)} invalid evolution references" if errors else "All evolution chains valid"
        )
    
    def test_type_distribution(self):
        """Analyze type distribution for balance."""
        logger.info("=== Analyzing Type Distribution ===")
        
        # Count Veramon by type
        type_count = {}
        for veramon in self.veramon_data.values():
            if 'type' in veramon and isinstance(veramon['type'], list):
                for t in veramon['type']:
                    type_count[t] = type_count.get(t, 0) + 1
        
        # Calculate percentages
        total = len(self.veramon_data)
        type_percent = {t: (count / total) * 100 for t, count in type_count.items()}
        
        # Sort by frequency
        sorted_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)
        
        # Format message
        message = "Type distribution:\n"
        for t, count in sorted_types:
            message += f"  - {t}: {count} ({type_percent[t]:.1f}%)\n"
        
        # Evaluate balance
        max_percent = max(type_percent.values())
        min_percent = min(type_percent.values())
        balanced = (max_percent - min_percent) <= 15.0  # Less than 15% difference is considered balanced
        
        self.record_result(
            "Type Distribution", 
            "data", 
            balanced, 
            f"Type range: {min_percent:.1f}% - {max_percent:.1f}%"
        )
    
    def test_rarity_distribution(self):
        """Analyze rarity distribution for balance."""
        logger.info("=== Analyzing Rarity Distribution ===")
        
        # Count Veramon by rarity
        rarity_count = {}
        for veramon in self.veramon_data.values():
            if 'rarity' in veramon:
                rarity = veramon['rarity']
                rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        # Calculate percentages
        total = len(self.veramon_data)
        rarity_percent = {r: (count / total) * 100 for r, count in rarity_count.items()}
        
        # Expected ranges for a balanced distribution
        expected_ranges = {
            'common': (15, 30),     # 15-30%
            'uncommon': (25, 40),   # 25-40%
            'rare': (25, 45),       # 25-45%
            'legendary': (2, 10),   # 2-10%
            'mythic': (1, 5)        # 1-5%
        }
        
        # Check if distribution is within expected ranges
        balanced = True
        for rarity, (min_pct, max_pct) in expected_ranges.items():
            if rarity in rarity_percent:
                pct = rarity_percent[rarity]
                if pct < min_pct or pct > max_pct:
                    balanced = False
                    break
        
        # Format message
        message = "Rarity distribution:\n"
        for rarity in ['common', 'uncommon', 'rare', 'legendary', 'mythic']:
            if rarity in rarity_count:
                message += f"  - {rarity.capitalize()}: {rarity_count[rarity]} ({rarity_percent[rarity]:.1f}%)\n"
        
        self.record_result(
            "Rarity Distribution", 
            "data", 
            balanced, 
            message
        )
    
    #----------------------------------------------------------------------
    # DATABASE TESTS
    #----------------------------------------------------------------------
    
    def test_database_tables(self):
        """Test database tables existence and structure."""
        logger.info("=== Testing Database Tables ===")
        
        # List of expected tables
        expected_tables = [
            "users",
            "captures",
            "battles",
            "battle_participants",
            "battle_veramon",
            "battle_logs",
            "trades",
            "trade_items",
            "factions",
            "faction_members"
        ]
        
        # Get all tables in the database
        try:
            self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = set(row[0] for row in self.db_cursor.fetchall())
            
            # Check each expected table
            for table in expected_tables:
                exists = table in actual_tables
                
                if exists:
                    # Check table columns
                    self.db_cursor.execute(f"PRAGMA table_info({table})")
                    columns = self.db_cursor.fetchall()
                    
                    self.record_result(
                        f"Table: {table}", 
                        "database", 
                        len(columns) > 0, 
                        f"Found {len(columns)} columns"
                    )
                else:
                    self.record_result(f"Table: {table}", "database", False, "Table not found")
            
            # Also count total tables
            self.record_result(
                "Total Tables", 
                "database", 
                True, 
                f"Found {len(actual_tables)} database tables"
            )
        except Exception as e:
            self.record_result("Database Tables", "database", False, str(e))
    
    def test_database_indices(self):
        """Test database indices for performance."""
        logger.info("=== Testing Database Indices ===")
        
        # Key indices for performance
        important_indices = [
            {"table": "battles", "column": "status"},
            {"table": "captures", "column": "user_id"},
            {"table": "battle_participants", "column": "battle_id"},
            {"table": "battle_veramon", "column": "battle_id"},
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
                
                self.record_result(
                    f"Index: {table}.{column}", 
                    "database", 
                    result is not None,
                    "Index found" if result else "Index missing"
                )
            except Exception as e:
                self.record_result(f"Index: {table}.{column}", "database", False, str(e))
    
    def test_database_connections(self):
        """Test database connection mechanisms."""
        logger.info("=== Testing Database Connections ===")
        
        try:
            # Test getting a new connection
            conn, conn_time = self.time_execution(get_connection)
            self.record_result(
                "Connection Creation", 
                "database", 
                conn is not None, 
                f"Created in {conn_time:.2f}ms",
                conn_time
            )
            
            # Test a simple query
            cursor = conn.cursor()
            query_result, query_time = self.time_execution(
                lambda: cursor.execute("SELECT 1").fetchone()
            )
            
            self.record_result(
                "Query Execution", 
                "database", 
                query_result is not None, 
                f"Executed in {query_time:.2f}ms",
                query_time
            )
            
            # Close connection
            conn.close()
        except Exception as e:
            self.record_result("Database Connection", "database", False, str(e))
    
    #----------------------------------------------------------------------
    # BATTLE SYSTEM TESTS
    #----------------------------------------------------------------------
    
    def test_battle_system(self):
        """Test battle system components."""
        logger.info("=== Testing Battle System ===")
        
        if not HAS_BATTLE_SYSTEM:
            self.record_result(
                "Battle System", 
                "battle", 
                False, 
                "Battle system modules not accessible"
            )
            return
        
        # Test battle model structure
        expected_methods = [
            'execute_move', 
            'add_participant',
            'add_veramon',
            'set_active_veramon',
            'start_battle'
        ]
        
        missing_methods = [
            method for method in expected_methods 
            if not hasattr(Battle, method)
        ]
        
        self.record_result(
            "Battle Model Structure", 
            "battle", 
            len(missing_methods) == 0, 
            f"Missing methods: {', '.join(missing_methods)}" if missing_methods else "All expected methods present"
        )
        
        # Check battle database schema
        try:
            # Test for presence of required battle columns
            self.db_cursor.execute("PRAGMA table_info(battles)")
            battle_columns = {col[1] for col in self.db_cursor.fetchall()}
            
            required_columns = {'battle_id', 'type', 'status', 'created_at'}
            missing_columns = required_columns - battle_columns
            
            self.record_result(
                "Battle Table Schema", 
                "battle", 
                len(missing_columns) == 0, 
                f"Missing columns: {', '.join(missing_columns)}" if missing_columns else "All required columns present"
            )
        except Exception as e:
            self.record_result("Battle Table Schema", "battle", False, str(e))
    
    def test_battle_compatibility(self):
        """Test Veramon compatibility with the battle system."""
        logger.info("=== Testing Battle Compatibility ===")
        
        error_count = 0
        
        # Check for battle compatibility
        for name, veramon in self.veramon_data.items():
            # Required for battles
            if 'base_stats' not in veramon:
                error_count += 1
                continue
                
            # Check stats structure
            stats = veramon.get('base_stats', {})
            for stat in ['hp', 'attack', 'defense', 'speed']:
                if stat not in stats or not isinstance(stats[stat], (int, float)):
                    error_count += 1
                    break
                    
            # Check moves
            if 'abilities' not in veramon or not veramon['abilities']:
                error_count += 1
                
            # Check types
            if 'type' not in veramon or not veramon['type']:
                error_count += 1
        
        self.record_result(
            "Battle Data Compatibility", 
            "battle", 
            error_count == 0, 
            f"Found {error_count} Veramon with battle incompatibilities" if error_count else "All Veramon are battle-compatible"
        )
    
    #----------------------------------------------------------------------
    # TRADING SYSTEM TESTS
    #----------------------------------------------------------------------
    
    def test_trading_system(self):
        """Test trading system components."""
        logger.info("=== Testing Trading System ===")
        
        if not HAS_TRADE_SYSTEM:
            self.record_result(
                "Trading System", 
                "trading", 
                False, 
                "Trading system modules not accessible"
            )
            return
        
        # Test trade model structure if available
        try:
            expected_methods = [
                'add_item', 
                'remove_item',
                'accept_trade',
                'cancel_trade',
                'get_status'
            ]
            
            missing_methods = [
                method for method in expected_methods 
                if not hasattr(Trade, method)
            ]
            
            self.record_result(
                "Trade Model Structure", 
                "trading", 
                len(missing_methods) == 0, 
                f"Missing methods: {', '.join(missing_methods)}" if missing_methods else "All expected methods present"
            )
        except Exception as e:
            self.record_result("Trade Model Structure", "trading", False, str(e))
        
        # Check trade database schema
        try:
            # Test for presence of required trade columns
            self.db_cursor.execute("PRAGMA table_info(trades)")
            trade_columns = {col[1] for col in self.db_cursor.fetchall()}
            
            required_columns = {'trade_id', 'status', 'created_at'}
            missing_columns = required_columns - trade_columns
            
            self.record_result(
                "Trade Table Schema", 
                "trading", 
                len(missing_columns) == 0, 
                f"Missing columns: {', '.join(missing_columns)}" if missing_columns else "All required columns present"
            )
        except Exception as e:
            self.record_result("Trade Table Schema", "trading", False, str(e))
    
    def test_trading_compatibility(self):
        """Test Veramon compatibility with the trading system."""
        logger.info("=== Testing Trading Compatibility ===")
        
        error_count = 0
        
        # Check for trading compatibility
        for name, veramon in self.veramon_data.items():
            # Required for trading - rarity affects value
            if 'rarity' not in veramon:
                error_count += 1
            
            # Name should match key for consistent trading display
            if veramon.get('name', '') != name:
                error_count += 1
        
        self.record_result(
            "Trading Data Compatibility", 
            "trading", 
            error_count == 0, 
            f"Found {error_count} Veramon with trading incompatibilities" if error_count else "All Veramon are trade-compatible"
        )
    
    #----------------------------------------------------------------------
    # UI COMPONENT TESTS
    #----------------------------------------------------------------------
    
    def test_ui_components(self):
        """Test UI components existence."""
        logger.info("=== Testing UI Components ===")
        
        # List of UI components to test
        ui_files = [
            {"path": "src/utils/ui/accessibility_ui.py", "name": "Accessibility UI"},
            {"path": "src/utils/ui/battle_ui.py", "name": "Battle UI"},
            {"path": "src/utils/ui/trade_ui.py", "name": "Trade UI"},
            {"path": "src/utils/ui/menu_ui.py", "name": "Menu UI"}
        ]
        
        # Check each UI component
        for ui in ui_files:
            file_path = os.path.join(parent_dir, ui["path"])
            exists = os.path.exists(file_path)
            
            self.record_result(
                ui["name"], 
                "ui", 
                exists, 
                "File exists" if exists else "File not found"
            )
    
    #----------------------------------------------------------------------
    # RUN ALL TESTS
    #----------------------------------------------------------------------
    
    def run_all_tests(self):
        """Run all tests and return results."""
        try:
            # Data Tests
            self.test_data_loading()
            self.test_veramon_structure()
            self.test_evolution_chains()
            self.test_type_distribution()
            self.test_rarity_distribution()
            
            # Database Tests
            self.test_database_tables()
            self.test_database_indices()
            self.test_database_connections()
            
            # Battle System Tests
            self.test_battle_system()
            self.test_battle_compatibility()
            
            # Trading System Tests
            self.test_trading_system()
            self.test_trading_compatibility()
            
            # UI Tests
            self.test_ui_components()
            
            # Print summary
            self.print_summary()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            raise
    
    def print_summary(self):
        """Print a summary of all test results."""
        logger.info("\n\n=== TEST SUMMARY ===")
        
        # Group results by category
        results_by_category = {}
        for result in self.results:
            if result.category not in results_by_category:
                results_by_category[result.category] = []
            results_by_category[result.category].append(result)
        
        total_passed = 0
        total_tests = len(self.results)
        
        # Print results for each category
        for category, results in results_by_category.items():
            passed = sum(1 for r in results if r.passed)
            category_name = self.categories.get(category, category.capitalize())
            
            if results:
                pass_rate = (passed / len(results)) * 100
                logger.info(f"{category_name}: {passed}/{len(results)} passed ({pass_rate:.1f}%)")
                
                # List failed tests
                if passed < len(results):
                    logger.info("  Failed tests:")
                    for r in results:
                        if not r.passed:
                            logger.info(f"    - {r.name}: {r.message}")
            
            total_passed += passed
        
        # Print overall summary
        if total_tests > 0:
            overall_pass_rate = (total_passed / total_tests) * 100
            logger.info(f"\nOverall: {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%)")
            
            if total_passed == total_tests:
                logger.info("All tests PASSED!")
            else:
                logger.info(f"{total_tests - total_passed} tests FAILED")

if __name__ == "__main__":
    print(f"Running Veramon Bot Test Suite {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    
    runner = VeramonTestSuite()
    runner.run_all_tests()
