#!/usr/bin/env python
"""
Test Runner for Veramon Reunited

This script provides a simple way to run all tests or specific test suites
for the Veramon Reunited project. It's useful for testing the new evolution,
forms, and weather systems.

Usage:
  python run_tests.py             # Run all tests
  python run_tests.py evolution   # Run only evolution tests
  python run_tests.py exploration # Run only exploration tests
  python run_tests.py performance # Run only performance tests
"""

import sys
import unittest
import os

def run_tests(test_pattern=None):
    """
    Run tests matching the given pattern or all tests if none specified.
    
    Args:
        test_pattern (str, optional): Filter tests by this pattern.
    """
    # Create test loader
    loader = unittest.TestLoader()
    
    # Print header
    print("\n" + "="*80)
    print(f"RUNNING VERAMON REUNITED TESTS: {test_pattern or 'ALL'}")
    print("="*80 + "\n")
    
    # Load tests
    if test_pattern:
        test_pattern = f"*{test_pattern}*"
        tests = loader.discover('tests', pattern=test_pattern)
        if tests.countTestCases() == 0:
            print(f"No tests found matching pattern: {test_pattern}")
            print("Available test files:")
            for f in os.listdir('tests'):
                if f.endswith('.py') and f != '__init__.py':
                    print(f"  - {f}")
            return
    else:
        tests = loader.discover('tests')
    
    # Create runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(tests)
    
    # Print summary
    print("\n" + "="*80)
    print(f"TEST RESULTS: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    print(f"  Ran {result.testsRun} tests")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("="*80 + "\n")
    
    return result

if __name__ == "__main__":
    # Determine test pattern from command line args
    pattern = None
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    
    # Run tests
    result = run_tests(pattern)
    
    # Set exit code based on test success
    sys.exit(0 if result.wasSuccessful() else 1)
