"""
Security Integration for Veramon Reunited
 2025 killerdash117 | https://github.com/killerdash117

This module provides the entry points to integrate all security subsystems
into the main codebase. It serves as the primary interface for security validations
across all game features.
"""

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
import logging

# Import all security subsystems
from src.core.security_manager import get_security_manager, ActionType
from src.core.catch_security import get_catch_security
from src.core.battle_security import get_battle_security
from src.core.trade_security import get_trade_security
from src.core.economy_security import get_economy_security

# Set up logging
logger = logging.getLogger("security")

class SecurityIntegration:
    """
    Provides integration points for all security subsystems.
    
    This class serves as the main interface for cogs and other code
    to interact with the security system. It ensures all security validations
    are properly applied across the game features.
    """
    
    @staticmethod
    async def validate_catch_flow(
        user_id: str, 
        biome: str, 
        special_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate all aspects of the catching flow from exploration to spawn.
        
        Args:
            user_id: ID of the user
            biome: Biome to explore
            special_area: Optional special area
        
        Returns:
            Dict: Validation results
        """
        catch_security = get_catch_security()
        return catch_security.validate_spawn(user_id, biome, special_area)
    
    @staticmethod
    async def validate_catch_attempt(
        user_id: str, 
        spawn_id: str, 
        item_id: str
    ) -> Dict[str, Any]:
        """
        Validate a catch attempt.
        
        Args:
            user_id: ID of the user
            spawn_id: ID of the spawned Veramon
            item_id: ID of the item used
        
        Returns:
            Dict: Validation results
        """
        catch_security = get_catch_security()
        result = catch_security.validate_catch_attempt(user_id, spawn_id, item_id)
        
        if result["valid"]:
            # Generate secure catch seed for catch rate calculation
            timestamp = datetime.utcnow().isoformat()
            catch_seed = catch_security.generate_catch_seed(user_id, spawn_id, timestamp)
            
            # Calculate catch rate securely
            catch_rate = catch_security.calculate_catch_rate(
                user_id, 
                result["veramon_id"], 
                result["rarity"], 
                item_id, 
                catch_seed
            )
            
            # Determine catch success
            success = catch_security.verify_catch_success(catch_rate, catch_seed)
            
            # Log the attempt
            catch_security.log_catch_attempt(
                user_id, 
                spawn_id, 
                item_id, 
                success, 
                result["veramon_id"], 
                result["rarity"]
            )
            
            # Add catch results to the validation result
            result["success"] = success
            result["catch_rate"] = catch_rate
        
        return result
    
    @staticmethod
    async def validate_battle_creation(
        user_id: str, 
        battle_type: str, 
        opponent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate battle creation.
        
        Args:
            user_id: ID of the user
            battle_type: Type of battle
            opponent_id: Optional opponent ID
        
        Returns:
            Dict: Validation results
        """
        battle_security = get_battle_security()
        return battle_security.validate_battle_creation(user_id, battle_type, opponent_id)
    
    @staticmethod
    async def validate_battle_action(
        user_id: str, 
        battle_id: int, 
        action_type: str, 
        action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a battle action.
        
        Args:
            user_id: ID of the user
            battle_id: ID of the battle
            action_type: Type of action
            action_data: Data for the action
        
        Returns:
            Dict: Validation results
        """
        battle_security = get_battle_security()
        return battle_security.validate_battle_action(
            user_id, battle_id, action_type, action_data
        )
    
    @staticmethod
    async def calculate_battle_rewards(
        battle_id: int, 
        winner_id: str
    ) -> Dict[str, Any]:
        """
        Calculate fair battle rewards.
        
        Args:
            battle_id: ID of the battle
            winner_id: ID of the winner
        
        Returns:
            Dict: Reward details
        """
        battle_security = get_battle_security()
        return battle_security.validate_battle_rewards(battle_id, winner_id)
    
    @staticmethod
    async def check_battle_timeout(battle_id: int) -> bool:
        """
        Check if a battle has timed out due to inactivity.
        
        Args:
            battle_id: ID of the battle
        
        Returns:
            bool: True if timed out
        """
        battle_security = get_battle_security()
        return battle_security.check_battle_timeout(battle_id)
    
    @staticmethod
    async def validate_trade_creation(
        user_id: str, 
        target_id: str
    ) -> Dict[str, Any]:
        """
        Validate trade creation.
        
        Args:
            user_id: ID of the user
            target_id: ID of the target
        
        Returns:
            Dict: Validation results
        """
        trade_security = get_trade_security()
        return trade_security.validate_trade_creation(user_id, target_id)
    
    @staticmethod
    async def validate_trade_action(
        trade_id: int, 
        user_id: str, 
        action: str, 
        item_id: Optional[int] = None,
        item_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a trade action.
        
        Args:
            trade_id: ID of the trade
            user_id: ID of the user
            action: Type of action
            item_id: Optional item ID
            item_type: Optional item type
        
        Returns:
            Dict: Validation results
        """
        trade_security = get_trade_security()
        return trade_security.validate_trade_action(
            trade_id, user_id, action, item_id, item_type
        )
    
    @staticmethod
    async def process_trade_completion(trade_id: int) -> Dict[str, Any]:
        """
        Process trade completion securely.
        
        Args:
            trade_id: ID of the trade
        
        Returns:
            Dict: Processing results
        """
        trade_security = get_trade_security()
        return trade_security.process_trade_completion(trade_id)
    
    @staticmethod
    async def validate_token_transaction(
        user_id: str, 
        amount: int, 
        transaction_type: str,
        recipient_id: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate token transaction.
        
        Args:
            user_id: ID of the user
            amount: Amount of tokens
            transaction_type: Type of transaction
            recipient_id: Optional recipient ID
            item_id: Optional item ID
        
        Returns:
            Dict: Validation results
        """
        economy_security = get_economy_security()
        result = economy_security.validate_token_transaction(
            user_id, amount, transaction_type, recipient_id, item_id
        )
        
        if result["valid"] and transaction_type != "check":
            # Log the transaction
            economy_security.log_transaction(
                user_id, 
                transaction_type, 
                amount, 
                item_id, 
                recipient_id
            )
        
        return result
    
    @staticmethod
    async def validate_shop_purchase(
        user_id: str, 
        item_id: str, 
        quantity: int,
        shop_type: str = "main"
    ) -> Dict[str, Any]:
        """
        Validate a shop purchase.
        
        Args:
            user_id: ID of the user
            item_id: ID of the item
            quantity: Quantity to purchase
            shop_type: Type of shop
        
        Returns:
            Dict: Validation results
        """
        economy_security = get_economy_security()
        return economy_security.validate_shop_purchase(
            user_id, item_id, quantity, shop_type
        )
    
    @staticmethod
    async def validate_profile_view(
        user_id: str,
        target_id: str
    ) -> Dict[str, Any]:
        """
        Validate if a user can view another user's profile.
        
        Args:
            user_id: ID of the user viewing the profile
            target_id: ID of the user whose profile is being viewed
            
        Returns:
            Dict: Validation results
        """
        # By default, users can view any profile
        # Rate limiting is applied to prevent abuse
        security_manager = get_security_manager()
        
        # Check rate limit for profile views
        rate_limited = not security_manager.check_rate_limit(
            user_id, ActionType.PROFILE_VIEW, 30, 60  # Max 30 profile views per minute
        )
        
        if rate_limited:
            return {
                "valid": False,
                "error": "You're viewing profiles too quickly. Please try again in a moment."
            }
            
        # No other restrictions
        return {
            "valid": True
        }
    
    @staticmethod
    async def validate_leaderboard_view(
        user_id: str,
        category: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Validate if a user can view a leaderboard.
        
        Args:
            user_id: ID of the user
            category: Leaderboard category
            timeframe: Timeframe for the leaderboard
            
        Returns:
            Dict: Validation results
        """
        # Apply rate limiting to prevent leaderboard spam
        security_manager = get_security_manager()
        
        # Check rate limit for leaderboard views
        rate_limited = not security_manager.check_rate_limit(
            user_id, ActionType.LEADERBOARD_VIEW, 10, 60  # Max 10 leaderboard views per minute
        )
        
        if rate_limited:
            return {
                "valid": False,
                "error": "You're viewing leaderboards too quickly. Please try again in a moment."
            }
            
        # Validate category
        valid_categories = ["tokens", "collection", "battles", "shinies", "trades"]
        if category not in valid_categories:
            return {
                "valid": False,
                "error": f"Invalid leaderboard category. Valid categories: {', '.join(valid_categories)}"
            }
            
        # Validate timeframe
        valid_timeframes = ["all", "month", "week"]
        if timeframe not in valid_timeframes:
            return {
                "valid": False,
                "error": f"Invalid timeframe. Valid timeframes: {', '.join(valid_timeframes)}"
            }
            
        # No other restrictions
        return {
            "valid": True
        }
    
    @staticmethod
    async def validate_transaction_history_view(
        user_id: str,
        transaction_type: str,
        limit: int
    ) -> Dict[str, Any]:
        """
        Validate if a user can view transaction history.
        
        Args:
            user_id: ID of the user
            transaction_type: Type of transactions to view
            limit: Number of transactions to view
            
        Returns:
            Dict: Validation results
        """
        # Apply rate limiting
        security_manager = get_security_manager()
        
        # Check rate limit for transaction history views
        rate_limited = not security_manager.check_rate_limit(
            user_id, ActionType.TRANSACTION_HISTORY_VIEW, 10, 60  # Max 10 views per minute
        )
        
        if rate_limited:
            return {
                "valid": False,
                "error": "You're viewing transaction history too quickly. Please try again in a moment."
            }
            
        # Validate transaction type
        valid_types = ["all", "transfer", "purchase", "battle_reward", "daily_bonus"]
        if transaction_type not in valid_types:
            return {
                "valid": False,
                "error": f"Invalid transaction type. Valid types: {', '.join(valid_types)}"
            }
            
        # Validate limit
        if limit <= 0 or limit > 50:  # Cap at 50 for performance
            return {
                "valid": False,
                "error": "Limit must be between 1 and 50."
            }
            
        # No other restrictions
        return {
            "valid": True
        }
    
    @staticmethod
    async def validate_team_action(
        user_id: str,
        action: str,
        team_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate team management actions.
        
        Args:
            user_id: ID of the user
            action: Action to perform (create, edit, view, list, delete, rename)
            team_name: Name of the team
            
        Returns:
            Dict: Validation results
        """
        # Apply rate limiting for team actions
        security_manager = get_security_manager()
        
        # Different rate limits for different actions
        if action in ["create", "delete", "rename"]:
            # Stricter limits for actions that modify data
            rate_limited = not security_manager.check_rate_limit(
                user_id, ActionType.TEAM_MODIFY, 5, 60  # Max 5 team modifications per minute
            )
        else:
            # More lenient limits for viewing actions
            rate_limited = not security_manager.check_rate_limit(
                user_id, ActionType.TEAM_VIEW, 20, 60  # Max 20 team views per minute
            )
            
        if rate_limited:
            return {
                "valid": False,
                "error": "You're managing teams too quickly. Please try again in a moment."
            }
            
        # Validate action
        valid_actions = ["create", "edit", "view", "list", "delete", "rename"]
        if action not in valid_actions:
            return {
                "valid": False,
                "error": f"Invalid team action. Valid actions: {', '.join(valid_actions)}"
            }
            
        # For certain actions, team_name is required
        if action in ["create", "edit", "view", "delete", "rename"] and not team_name:
            return {
                "valid": False,
                "error": f"Team name is required for {action} action."
            }
            
        # If team name is provided, validate it
        if team_name and len(team_name) > 32:
            return {
                "valid": False,
                "error": "Team name cannot exceed 32 characters."
            }
            
        # No other restrictions
        return {
            "valid": True
        }
    
    @staticmethod
    async def validate_team_member_action(
        user_id: str,
        team_name: str,
        action: str,
        capture_id: Optional[int] = None,
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate team member management actions.
        
        Args:
            user_id: ID of the user
            team_name: Name of the team
            action: Action to perform (add, remove)
            capture_id: ID of the capture to add
            position: Position in the team
            
        Returns:
            Dict: Validation results
        """
        # Apply rate limiting
        security_manager = get_security_manager()
        
        # Check rate limit for team member modifications
        rate_limited = not security_manager.check_rate_limit(
            user_id, ActionType.TEAM_MEMBER_MODIFY, 10, 60  # Max 10 team member modifications per minute
        )
        
        if rate_limited:
            return {
                "valid": False,
                "error": "You're modifying team members too quickly. Please try again in a moment."
            }
            
        # Validate action
        valid_actions = ["add", "remove"]
        if action not in valid_actions:
            return {
                "valid": False,
                "error": f"Invalid team member action. Valid actions: {', '.join(valid_actions)}"
            }
            
        # Validate team name
        if not team_name:
            return {
                "valid": False,
                "error": "Team name is required."
            }
            
        # Validate position
        if position is None:
            return {
                "valid": False,
                "error": "Position is required."
            }
            
        if position < 1 or position > 6:  # Max team size is 6
            return {
                "valid": False,
                "error": "Position must be between 1 and 6."
            }
            
        # For "add" action, capture_id is required
        if action == "add" and capture_id is None:
            return {
                "valid": False,
                "error": "Capture ID is required for add action."
            }
            
        # No other restrictions
        return {
            "valid": True
        }
    
    @staticmethod
    async def log_security_event(
        user_id: str,
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log a security event for monitoring.
        
        Args:
            user_id: ID of the user
            event_type: Type of event
            details: Event details
        """
        security_manager = get_security_manager()
        security_manager.log_security_event(
            user_id=user_id,
            event_type=event_type,
            details=details
        )
    
    @staticmethod
    async def validate_db_command_access(
        user_id: str,
        command_name: str,
        required_role: str = "admin"
    ) -> Dict[str, Any]:
        """
        Validate if a user can access database management commands.
        
        This method enforces a two-tier access system:
        - 'dev' role can access ALL database commands (including destructive ones)
        - 'admin' role can only access a subset of safer database commands
        
        Args:
            user_id: ID of the user
            command_name: The database command being accessed
            required_role: Minimum role required ('admin' or 'dev')
            
        Returns:
            Dict: Validation results
        """
        security_manager = get_security_manager()
        
        # First check if user has developer role (highest privilege)
        is_dev = security_manager.check_user_role(user_id, "developer")
        
        # If dev role is required and user doesn't have it, deny access
        if required_role == "dev" and not is_dev:
            return {
                "valid": False,
                "error": "This command requires developer privileges."
            }
            
        # If admin role is required, check if user has admin OR dev role
        if required_role == "admin":
            is_admin = security_manager.check_user_role(user_id, "admin")
            if not (is_admin or is_dev):
                return {
                    "valid": False,
                    "error": "This command requires administrator privileges."
                }
        
        # Define dangerous commands that only devs should access
        dev_only_commands = ["db_reset", "db_restore", "db_clear_table"]
        
        # If command is in dev_only list but user is not dev, deny access
        if command_name in dev_only_commands and not is_dev:
            return {
                "valid": False,
                "error": f"The {command_name} command requires developer privileges due to its potential impact."
            }
            
        # Apply rate limiting based on command impact
        high_impact_commands = ["db_optimize", "db_backup"]
        
        if command_name in high_impact_commands:
            # Limit high-impact commands to prevent server overload
            rate_limited = not security_manager.check_rate_limit(
                user_id, ActionType.DB_MANAGEMENT, 5, 300  # Max 5 high-impact DB operations per 5 minutes
            )
        else:
            # Lower rate limit for standard commands
            rate_limited = not security_manager.check_rate_limit(
                user_id, ActionType.DB_INFO, 10, 60  # Max 10 standard DB operations per minute
            )
            
        if rate_limited:
            return {
                "valid": False,
                "error": "You're performing database operations too frequently. Please wait a moment."
            }
        
        # Log the database command access for security auditing
        security_manager.log_security_event(
            user_id=user_id,
            event_type="database_access",
            details={
                "command": command_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "valid": True
        }

# Singleton instance
_security_integration = None

def get_security_integration() -> SecurityIntegration:
    """
    Get the global security integration instance.
    
    Returns:
        SecurityIntegration: Global security integration instance
    """
    global _security_integration
    
    if _security_integration is None:
        _security_integration = SecurityIntegration()
        
    return _security_integration
