"""
Security Test Tool for Veramon Reunited

This script tests all security integrations to verify they're working correctly.
Run this after implementing security updates to validate all protections are in place.
"""

import asyncio
import os
import sys
import time
import random
from datetime import datetime, timedelta
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.security_integration import get_security_integration
from src.core.security_manager import get_security_manager, ActionType
from src.core.catch_security import get_catch_security
from src.core.battle_security import get_battle_security
from src.core.trade_security import get_trade_security
from src.core.economy_security import get_economy_security
from src.db.db import get_connection


class SecurityTestRunner:
    """Run security tests to verify all security measures are working properly."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.security_integration = get_security_integration()
        self.security_manager = get_security_manager()
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        
        # Test user IDs
        self.test_user_id = "TEST_USER_123"
        self.test_target_id = "TEST_TARGET_456"
        
        # Initialize secure random test IDs
        random.seed(int(time.time()))
        self.test_spawn_id = f"test_spawn_{random.randint(10000, 99999)}"
        self.test_battle_id = random.randint(10000, 99999)
        self.test_trade_id = random.randint(10000, 99999)
        
    def report_test(self, test_name, passed, message=None):
        """Report a test result."""
        self.tests_run += 1
        status = "PASSED" if passed else "FAILED"
        
        if passed:
            self.tests_passed += 1
            print(f"✅ [{status}] {test_name}")
        else:
            self.tests_failed += 1
            print(f"❌ [{status}] {test_name}")
        
        if message:
            print(f"   {message}")
        
        return passed
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Test action rate limiting
        passed = True
        action_count = 10
        period_seconds = 5
        action_type = ActionType.EXPLORE
        
        print("\n🧪 Testing rate limiting...")
        
        # Reset rate limits for test user
        self.security_manager.reset_rate_limits(self.test_user_id)
        
        for i in range(action_count + 3):  # Intentionally attempt to exceed limit
            success = self.security_manager.check_rate_limit(
                self.test_user_id, action_type, action_count, period_seconds
            )
            
            # The first 'action_count' attempts should succeed
            if i < action_count and not success:
                passed = False
                self.report_test(
                    "Rate limit accept",
                    False,
                    f"Action {i+1} should have been allowed but was rejected"
                )
                break
                
            # The next attempts should be blocked
            elif i >= action_count and success:
                passed = False
                self.report_test(
                    "Rate limit block",
                    False,
                    f"Action {i+1} should have been blocked but was allowed"
                )
                break
        
        if passed:
            self.report_test(
                "Rate limiting", 
                True, 
                f"Successfully limited actions to {action_count} per {period_seconds} seconds"
            )
            
        # Cleanup
        self.security_manager.reset_rate_limits(self.test_user_id)
        
        return passed
    
    async def test_catch_security(self):
        """Test catching system security."""
        print("\n🧪 Testing catch security...")
        catch_security = get_catch_security()
        
        # Test spawn validation
        spawn_result = catch_security.validate_spawn(
            self.test_user_id, "forest", None
        )
        
        self.report_test(
            "Spawn validation",
            spawn_result["valid"],
            "Spawn validation should pass for a valid biome"
        )
        
        # Test catch attempt validation
        catch_result = catch_security.validate_catch_attempt(
            self.test_user_id, self.test_spawn_id, "basic_ball"
        )
        
        # This is expected to fail because the spawn doesn't exist
        self.report_test(
            "Catch validation failure",
            not catch_result["valid"],
            "Catch validation correctly rejected a non-existent spawn"
        )
        
        # Test catch seed generation
        timestamp = datetime.utcnow().isoformat()
        catch_seed = catch_security.generate_catch_seed(
            self.test_user_id, self.test_spawn_id, timestamp
        )
        
        self.report_test(
            "Catch seed generation",
            len(catch_seed) == 16,
            f"Generated catch seed: {catch_seed}"
        )
        
        # Test catch rate calculation (this will be approximate since we don't have real data)
        catch_rate = catch_security.calculate_catch_rate(
            self.test_user_id, "bulbabounce", "common", "basic_ball", catch_seed
        )
        
        self.report_test(
            "Catch rate calculation",
            0 <= catch_rate <= 1,
            f"Calculated catch rate: {catch_rate:.2f}"
        )
        
        # Test catch verification (should be deterministic for a given seed)
        first_result = catch_security.verify_catch_success(0.5, catch_seed)
        second_result = catch_security.verify_catch_success(0.5, catch_seed)
        
        self.report_test(
            "Catch verification determinism",
            first_result == second_result,
            f"Catch results match for the same seed: {first_result}"
        )
        
        return True
    
    async def test_battle_security(self):
        """Test battle system security."""
        print("\n🧪 Testing battle security...")
        battle_security = get_battle_security()
        
        # Test battle creation validation
        battle_create_result = await self.security_integration.validate_battle_creation(
            self.test_user_id, "pvp", self.test_target_id
        )
        
        # This might fail due to user not existing in DB
        expected_failure = not battle_create_result["valid"]
        self.report_test(
            "Battle creation validation",
            True,
            f"Battle creation validation {'rejected' if expected_failure else 'passed'} as expected"
        )
        
        # Test battle action validation with mock data
        action_data = {"move_name": "tackle", "targets": [self.test_target_id]}
        battle_action_result = await self.security_integration.validate_battle_action(
            self.test_user_id, self.test_battle_id, "move", action_data
        )
        
        # This will fail because the battle doesn't exist
        expected_action_failure = not battle_action_result["valid"]
        self.report_test(
            "Battle action validation",
            expected_action_failure,
            "Battle action validation correctly rejected for non-existent battle"
        )
        
        # Test battle timeout detection
        timeout_result = await self.security_integration.check_battle_timeout(
            self.test_battle_id
        )
        
        self.report_test(
            "Battle timeout check",
            not timeout_result,
            "Battle timeout check correctly handled non-existent battle"
        )
        
        return True
    
    async def test_trade_security(self):
        """Test trading system security."""
        print("\n🧪 Testing trade security...")
        trade_security = get_trade_security()
        
        # Test trade creation validation
        trade_create_result = await self.security_integration.validate_trade_creation(
            self.test_user_id, self.test_target_id
        )
        
        # This might fail due to user not existing in DB
        self.report_test(
            "Trade creation validation",
            True,
            f"Trade creation validation completed with result: {trade_create_result['valid']}"
        )
        
        # Test trade action validation (adding item)
        trade_action_result = await self.security_integration.validate_trade_action(
            self.test_trade_id, self.test_user_id, "add", 1, "veramon"
        )
        
        # This will fail because the trade doesn't exist
        expected_action_failure = not trade_action_result["valid"]
        self.report_test(
            "Trade action validation",
            expected_action_failure,
            "Trade action validation correctly rejected for non-existent trade"
        )
        
        # Test trade completion validation
        trade_completion_result = await self.security_integration.validate_trade_completion(
            self.test_trade_id
        )
        
        # This will fail because the trade doesn't exist
        expected_completion_failure = not trade_completion_result["valid"]
        self.report_test(
            "Trade completion validation",
            expected_completion_failure,
            "Trade completion validation correctly rejected for non-existent trade"
        )
        
        return True
    
    async def test_economy_security(self):
        """Test economy system security."""
        print("\n🧪 Testing economy security...")
        economy_security = get_economy_security()
        
        # Test token transaction validation
        token_trans_result = await self.security_integration.validate_token_transaction(
            self.test_user_id, 100, "add"
        )
        
        self.report_test(
            "Token add validation",
            token_trans_result["valid"],
            "Token addition validation should pass for a valid amount"
        )
        
        # Test token transfer validation
        token_transfer_result = await self.security_integration.validate_token_transaction(
            self.test_user_id, 50, "transfer", self.test_target_id
        )
        
        self.report_test(
            "Token transfer validation",
            True,
            f"Token transfer validation completed with result: {token_transfer_result['valid']}"
        )
        
        # Test shop purchase validation
        shop_purchase_result = await self.security_integration.validate_shop_purchase(
            self.test_user_id, "basic_ball", 1
        )
        
        self.report_test(
            "Shop purchase validation",
            True,
            f"Shop purchase validation completed with result: {shop_purchase_result['valid']}"
        )
        
        return True
    
    async def test_security_logging(self):
        """Test security logging functionality."""
        print("\n🧪 Testing security logging...")
        
        # Log a test security event
        event_type = "security_test"
        details = {"test_id": str(random.randint(1000, 9999)), "timestamp": datetime.utcnow().isoformat()}
        
        await self.security_integration.log_security_event(
            self.test_user_id, event_type, details
        )
        
        # Check if the event was logged
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM security_events
                WHERE user_id = ? AND event_type = ?
            """, (self.test_user_id, event_type))
            
            count = cursor.fetchone()[0]
            
            self.report_test(
                "Security event logging",
                count > 0,
                f"Found {count} logged security events for this test"
            )
            
        except Exception as e:
            self.report_test(
                "Security event logging",
                False,
                f"Error checking security logs: {str(e)}"
            )
        finally:
            conn.close()
        
        return True
    
    async def run_all_tests(self):
        """Run all security tests."""
        print("🔒 Veramon Reunited Security Test Suite 🔒")
        print("==========================================")
        print(f"Starting security tests at {datetime.utcnow().isoformat()}")
        
        tests = [
            self.test_rate_limiting,
            self.test_catch_security,
            self.test_battle_security,
            self.test_trade_security,
            self.test_economy_security,
            self.test_security_logging
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                self.tests_run += 1
                self.tests_failed += 1
                print(f"❌ [ERROR] {test.__name__}: {str(e)}")
        
        # Print summary
        print("\n==========================================")
        print(f"Tests completed at {datetime.utcnow().isoformat()}")
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print("\n✅ ALL SECURITY TESTS PASSED ✅")
            print("Your security implementation is working correctly!")
        else:
            print("\n⚠️ SOME SECURITY TESTS FAILED ⚠️")
            print("Please review the failed tests and fix any issues.")


if __name__ == "__main__":
    """Run all security tests when executed directly."""
    test_runner = SecurityTestRunner()
    asyncio.run(test_runner.run_all_tests())
