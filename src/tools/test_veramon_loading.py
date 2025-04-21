"""
Veramon Data Loading Test Tool
Created: April 21, 2025

This script tests loading Veramon data through the various loading methods
to ensure that they correctly use the new veramon_database.json file.
"""

import os
import sys
import time
import json
from pathlib import Path

# Add the parent directory to path so we can import the modules
script_dir = Path(__file__).resolve().parent
src_dir = script_dir.parent
project_dir = src_dir.parent
sys.path.append(str(project_dir))

# Now import the modules we need to test
from src.utils.data_loader import load_all_veramon_data
from src.utils.cache import get_veramon_data

def test_direct_loading():
    """Test direct loading of the veramon database file."""
    print("\n=== Testing Direct File Loading ===")
    
    data_dir = src_dir / 'data'
    database_path = data_dir / 'veramon_database.json'
    
    if not database_path.exists():
        print(f"ERROR: Database file not found: {database_path}")
        return False
    
    try:
        start_time = time.time()
        with open(database_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        elapsed = time.time() - start_time
        
        print(f"Successfully loaded database directly")
        print(f"  - File size: {database_path.stat().st_size / 1024:.2f} KB")
        print(f"  - Veramon count: {len(data)}")
        print(f"  - Loading time: {elapsed * 1000:.2f} ms")
        return True
    except Exception as e:
        print(f"ERROR: Failed to load database directly: {e}")
        return False

def test_data_loader():
    """Test loading through the data_loader module."""
    print("\n=== Testing Data Loader Module ===")
    
    try:
        start_time = time.time()
        data = load_all_veramon_data()
        elapsed = time.time() - start_time
        
        print(f"Successfully loaded through data_loader.load_all_veramon_data()")
        print(f"  - Veramon count: {len(data)}")
        print(f"  - Loading time: {elapsed * 1000:.2f} ms")
        return True
    except Exception as e:
        print(f"ERROR: Failed to load through data_loader: {e}")
        return False

def test_cache_module():
    """Test loading through the cache module."""
    print("\n=== Testing Cache Module ===")
    
    try:
        start_time = time.time()
        data = get_veramon_data()
        elapsed = time.time() - start_time
        
        print(f"Successfully loaded through cache.get_veramon_data()")
        print(f"  - Veramon count: {len(data)}")
        print(f"  - Loading time: {elapsed * 1000:.2f} ms")
        
        # Test getting a specific Veramon
        veramon_name = next(iter(data.keys()))
        start_time = time.time()
        specific_data = get_veramon_data(veramon_name)
        elapsed = time.time() - start_time
        
        print(f"Successfully retrieved specific Veramon: {veramon_name}")
        print(f"  - Retrieval time: {elapsed * 1000:.2f} ms")
        
        return True
    except Exception as e:
        print(f"ERROR: Failed to load through cache module: {e}")
        return False

def verify_data_consistency():
    """Verify that all loading methods return the same data."""
    print("\n=== Verifying Data Consistency ===")
    
    # Load data using different methods
    data_direct = None
    data_loader = None
    data_cache = None
    
    try:
        # Direct loading
        database_path = src_dir / 'data' / 'veramon_database.json'
        with open(database_path, 'r', encoding='utf-8') as f:
            data_direct = json.load(f)
        
        # Data loader
        data_loader = load_all_veramon_data()
        
        # Cache module
        data_cache = get_veramon_data()
        
        # Compare sizes
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
            
        # Check for specific Veramon
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
        
        return direct_count == loader_count == cache_count
    except Exception as e:
        print(f"ERROR: Failed to verify data consistency: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Veramon Data Loading Test ===")
    
    success = True
    
    # Run tests
    success = test_direct_loading() and success
    success = test_data_loader() and success
    success = test_cache_module() and success
    success = verify_data_consistency() and success
    
    # Print summary
    print("\n=== Test Summary ===")
    if success:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED! See above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
