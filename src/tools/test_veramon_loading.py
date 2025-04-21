"""
Enhanced Veramon Data Testing System
This script performs comprehensive testing of the Veramon data structure
to ensure compatibility with battle, trading, and other game systems.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))
sys.path.insert(0, parent_dir)

# Import the required modules
from src.utils.cache import get_veramon_data
from src.utils.data_loader import load_all_veramon_data

def measure_execution_time(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        return result, execution_time
    return wrapper

@measure_execution_time
def load_database_directly():
    """Load the Veramon database directly from the JSON file."""
    data_dir = os.path.join(parent_dir, 'src', 'data')
    database_path = os.path.join(data_dir, 'veramon_database.json')
    
    with open(database_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@measure_execution_time
def fetch_specific_veramon(data, name):
    """Fetch a specific Veramon from the data."""
    return data.get(name, {})

def check_veramon_structure(data: Dict[str, Any]) -> List[str]:
    """Check the structure of Veramon data."""
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
    
    for name, veramon in data.items():
        # Check for required fields
        for field in required_fields:
            if field not in veramon:
                errors.append(f"ERROR: {name} is missing required field: {field}")
        
        # Check types
        if 'type' in veramon:
            if not isinstance(veramon['type'], list):
                errors.append(f"ERROR: {name} 'type' should be a list, got {type(veramon['type'])}")
            else:
                for t in veramon['type']:
                    if t not in valid_types:
                        errors.append(f"ERROR: {name} has invalid type: {t}")
        
        # Check rarity
        if 'rarity' in veramon:
            if veramon['rarity'] not in valid_rarities:
                errors.append(f"ERROR: {name} has invalid rarity: {veramon['rarity']}")
        
        # Check base stats
        if 'base_stats' in veramon:
            if not isinstance(veramon['base_stats'], dict):
                errors.append(f"ERROR: {name} 'base_stats' should be a dict, got {type(veramon['base_stats'])}")
            else:
                required_stats = ['hp', 'atk', 'def', 'sp_atk', 'sp_def', 'speed']
                for stat in required_stats:
                    if stat not in veramon['base_stats']:
                        errors.append(f"ERROR: {name} is missing required stat: {stat}")
        
        # Check abilities
        if 'abilities' in veramon:
            if not isinstance(veramon['abilities'], list):
                errors.append(f"ERROR: {name} 'abilities' should be a list, got {type(veramon['abilities'])}")
        
        # Check numeric values
        if 'catch_rate' in veramon and not isinstance(veramon['catch_rate'], (int, float)):
            errors.append(f"ERROR: {name} 'catch_rate' should be numeric, got {type(veramon['catch_rate'])}")
        
        if 'shiny_rate' in veramon and not isinstance(veramon['shiny_rate'], (int, float)):
            errors.append(f"ERROR: {name} 'shiny_rate' should be numeric, got {type(veramon['shiny_rate'])}")
    
    return errors

def check_battle_system_compatibility(data: Dict[str, Any]) -> List[str]:
    """Check compatibility with the battle system."""
    errors = []
    
    for name, veramon in data.items():
        # For battle calculations, we need proper stats
        if 'base_stats' in veramon:
            stats = veramon['base_stats']
            for stat_name, value in stats.items():
                if not isinstance(value, (int, float)) or value <= 0:
                    errors.append(f"ERROR: {name} has invalid stat {stat_name}: {value}")
        
        # For battle moves, we need abilities
        if 'abilities' in veramon and not veramon['abilities']:
            errors.append(f"ERROR: {name} has no abilities for battle")
        
        # For damage calculations, we need proper types
        if 'type' in veramon and not veramon['type']:
            errors.append(f"ERROR: {name} has no types for damage calculation")
    
    return errors

def check_trading_system_compatibility(data: Dict[str, Any]) -> List[str]:
    """Check compatibility with the trading system."""
    errors = []
    
    for name, veramon in data.items():
        # For trading value calculations, we need proper rarity
        if 'rarity' not in veramon:
            errors.append(f"ERROR: {name} is missing rarity for trade value calculations")
        
        # For trading display, we need a name that matches the key
        if 'name' in veramon and veramon['name'] != name:
            errors.append(f"ERROR: {name} has mismatched name: {veramon['name']}")
    
    return errors

def test_evolutionary_chains(data: Dict[str, Any]) -> List[str]:
    """Verify that all evolution references are valid."""
    errors = []
    veramon_names = set(data.keys())
    
    for name, veramon in data.items():
        if 'evolution' in veramon and isinstance(veramon['evolution'], dict):
            if 'evolves_to' in veramon['evolution']:
                evolves_to = veramon['evolution']['evolves_to']
                if evolves_to not in veramon_names:
                    errors.append(f"ERROR: {name} evolves to non-existent Veramon: {evolves_to}")
            
            if 'evolution_level' in veramon['evolution']:
                level = veramon['evolution']['evolution_level']
                if not isinstance(level, int) or level <= 0:
                    errors.append(f"ERROR: {name} has invalid evolution level: {level}")
    
    return errors

def analyze_type_distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """Analyze the distribution of types in the database."""
    type_counts = {}
    
    for veramon in data.values():
        if 'type' in veramon and isinstance(veramon['type'], list):
            for t in veramon['type']:
                type_counts[t] = type_counts.get(t, 0) + 1
    
    return type_counts

def analyze_rarity_distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """Analyze the distribution of rarities in the database."""
    rarity_counts = {}
    
    for veramon in data.values():
        if 'rarity' in veramon:
            rarity = veramon['rarity']
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
    
    return rarity_counts

def print_section_header(title):
    """Print a formatted section header."""
    print(f"\n=== {title} ===")

def run_tests():
    """Run all tests on the Veramon data."""
    print("=== Veramon Data Loading Test ===")
    
    # Test 1: Direct file loading
    print_section_header("Testing Direct File Loading")
    data_direct, direct_time = load_database_directly()
    
    file_size = os.path.getsize(os.path.join(parent_dir, 'src', 'data', 'veramon_database.json')) / 1024
    print(f"Successfully loaded database directly")
    print(f"  - File size: {file_size:.2f} KB")
    print(f"  - Veramon count: {len(data_direct)}")
    print(f"  - Loading time: {direct_time:.2f} ms")
    
    # Test 2: Loading through data_loader module
    print_section_header("Testing Data Loader Module")
    data_loader, loader_time = measure_execution_time(load_all_veramon_data)()
    
    print(f"Successfully loaded through data_loader.load_all_veramon_data()")
    print(f"  - Veramon count: {len(data_loader)}")
    print(f"  - Loading time: {loader_time:.2f} ms")
    
    # Test 3: Loading through cache module
    print_section_header("Testing Cache Module")
    data_cache, cache_time = measure_execution_time(get_veramon_data)()
    
    print(f"Successfully loaded through cache.get_veramon_data()")
    print(f"  - Veramon count: {len(data_cache)}")
    print(f"  - Loading time: {cache_time:.2f} ms")
    
    # Test 4: Retrieving a specific Veramon
    test_veramon = next(iter(data_direct))  # Get the first Veramon name
    specific_veramon, retrieval_time = fetch_specific_veramon(data_cache, test_veramon)
    
    print(f"Successfully retrieved specific Veramon: {test_veramon}")
    print(f"  - Retrieval time: {retrieval_time:.2f} ms")
    
    # Test 5: Verify data consistency
    print_section_header("Verifying Data Consistency")
    
    direct_count = len(data_direct)
    loader_count = len(data_loader)
    cache_count = len(data_cache)
    
    print(f"Veramon count comparison:")
    print(f"  - Direct loading: {direct_count}")
    print(f"  - Data loader: {loader_count}")
    print(f"  - Cache module: {cache_count}")
    
    if direct_count == loader_count == cache_count:
        print(f"SUCCESS: All methods loaded the same number of Veramon: {direct_count}")
    else:
        print(f"WARNING: Different number of Veramon loaded by different methods")
        
    # Test 6: Check for specific Veramon availability
    veramon_check = ["Embering", "Aqualet", "Voltik", "Froslet"]
    print(f"\nChecking for specific Veramon availability:")
    
    for veramon in veramon_check:
        in_direct = veramon in data_direct
        in_loader = veramon in data_loader
        in_cache = veramon in data_cache
        
        if in_direct and in_loader and in_cache:
            print(f"  [PASS] {veramon} available in all methods")
        else:
            print(f"  [FAIL] {veramon} not available in all methods:")
            print(f"    - Direct: {'Yes' if in_direct else 'No'}")
            print(f"    - Loader: {'Yes' if in_loader else 'No'}")
            print(f"    - Cache: {'Yes' if in_cache else 'No'}")
    
    # Test 7: Check data structure
    print_section_header("Checking Data Structure")
    structure_errors = check_veramon_structure(data_direct)
    
    if structure_errors:
        print(f"Found {len(structure_errors)} structure issues:")
        for i, error in enumerate(structure_errors[:5], 1):
            print(f"  {i}. {error}")
        if len(structure_errors) > 5:
            print(f"  ... and {len(structure_errors) - 5} more issues")
    else:
        print("SUCCESS: All Veramon have valid data structure")
    
    # Test 8: Check battle system compatibility
    print_section_header("Checking Battle System Compatibility")
    battle_errors = check_battle_system_compatibility(data_direct)
    
    if battle_errors:
        print(f"Found {len(battle_errors)} battle system compatibility issues:")
        for i, error in enumerate(battle_errors[:5], 1):
            print(f"  {i}. {error}")
        if len(battle_errors) > 5:
            print(f"  ... and {len(battle_errors) - 5} more issues")
    else:
        print("SUCCESS: All Veramon are compatible with the battle system")
    
    # Test 9: Check trading system compatibility
    print_section_header("Checking Trading System Compatibility")
    trading_errors = check_trading_system_compatibility(data_direct)
    
    if trading_errors:
        print(f"Found {len(trading_errors)} trading system compatibility issues:")
        for i, error in enumerate(trading_errors[:5], 1):
            print(f"  {i}. {error}")
        if len(trading_errors) > 5:
            print(f"  ... and {len(trading_errors) - 5} more issues")
    else:
        print("SUCCESS: All Veramon are compatible with the trading system")
    
    # Test 10: Check evolutionary chains
    print_section_header("Checking Evolutionary Chains")
    evolution_errors = test_evolutionary_chains(data_direct)
    
    if evolution_errors:
        print(f"Found {len(evolution_errors)} evolution reference issues:")
        for i, error in enumerate(evolution_errors[:5], 1):
            print(f"  {i}. {error}")
        if len(evolution_errors) > 5:
            print(f"  ... and {len(evolution_errors) - 5} more issues")
    else:
        print("SUCCESS: All evolution references are valid")
    
    # Test 11: Analyze type distribution
    print_section_header("Type Distribution Analysis")
    type_counts = analyze_type_distribution(data_direct)
    
    print("Type distribution in the database:")
    for t, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {t}: {count} Veramon ({count/len(data_direct)*100:.1f}%)")
    
    # Test 12: Analyze rarity distribution
    print_section_header("Rarity Distribution Analysis")
    rarity_counts = analyze_rarity_distribution(data_direct)
    
    print("Rarity distribution in the database:")
    for r, count in sorted(rarity_counts.items(), key=lambda x: ("common", "uncommon", "rare", "legendary", "mythic").index(x[0])):
        print(f"  - {r.capitalize()}: {count} Veramon ({count/len(data_direct)*100:.1f}%)")
    
    # Overall test summary
    print_section_header("Test Summary")
    
    all_errors = structure_errors + battle_errors + trading_errors + evolution_errors
    if all_errors:
        print(f"Some tests FAILED! Found {len(all_errors)} issues across all tests.")
        print("See above for details.")
    else:
        print("All tests PASSED!")

if __name__ == "__main__":
    run_tests()
