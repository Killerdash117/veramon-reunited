import discord
from discord.ext import commands
import traceback
import sys
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union, Callable

# Set up logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Main logger configuration
logger = logging.getLogger('veramon')
logger.setLevel(logging.INFO)

# Handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# Handler for file output
file_handler = logging.FileHandler(os.path.join(LOG_DIR, 'veramon.log'))
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Handler for error logging specifically
error_handler = logging.FileHandler(os.path.join(LOG_DIR, 'errors.log'))
error_handler.setLevel(logging.ERROR)
error_format = logging.Formatter('%(asctime)s\n%(levelname)s: %(message)s\n---')
error_handler.setFormatter(error_format)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

class ErrorSeverity(Enum):
    """Severity levels for errors"""
    INFO = "info"           # Informational, not really an error
    LOW = "low"             # Minor error, doesn't affect functionality
    MEDIUM = "medium"       # Moderate error, affects some functionality
    HIGH = "high"           # Severe error, major functionality affected
    CRITICAL = "critical"   # Critical error, application may not function

class ErrorCategory(Enum):
    """Categories for different types of errors"""
    USER_INPUT = "user_input"       # Invalid user input
    PERMISSION = "permission"       # Permission-related issues
    DATABASE = "database"           # Database errors
    DISCORD_API = "discord_api"     # Discord API issues
    LOGIC = "logic"                 # Logic errors in code
    NETWORK = "network"             # Network-related issues
    RESOURCE = "resource"           # Resource not found or unavailable
    TIMEOUT = "timeout"             # Operation timed out
    UNKNOWN = "unknown"             # Unknown or uncategorized errors

class ErrorHandler:
    """
    A class to handle errors in a consistent way across the application.
    Provides user-friendly messages and proper logging.
    """
    
    # Dictionary of error messages by category
    ERROR_MESSAGES = {
        ErrorCategory.USER_INPUT: "There was a problem with your input. Please check and try again.",
        ErrorCategory.PERMISSION: "You don't have permission to do that.",
        ErrorCategory.DATABASE: "There was a database error. Please try again later.",
        ErrorCategory.DISCORD_API: "There was an issue with Discord. Please try again later.",
        ErrorCategory.LOGIC: "Something unexpected happened. Please try again.",
        ErrorCategory.NETWORK: "There was a network issue. Please try again later.",
        ErrorCategory.RESOURCE: "The requested resource couldn't be found.",
        ErrorCategory.TIMEOUT: "The operation timed out. Please try again.",
        ErrorCategory.UNKNOWN: "An unknown error occurred. Please try again later."
    }
    
    # Color mapping for embeds based on severity
    SEVERITY_COLORS = {
        ErrorSeverity.INFO: discord.Color.blue(),
        ErrorSeverity.LOW: discord.Color.green(),
        ErrorSeverity.MEDIUM: discord.Color.gold(),
        ErrorSeverity.HIGH: discord.Color.red(),
        ErrorSeverity.CRITICAL: discord.Color.dark_red()
    }
    
    @classmethod
    async def handle_error(
        cls,
        interaction: discord.Interaction,
        error: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        custom_message: Optional[str] = None,
        ephemeral: bool = True,
        log: bool = True
    ):
        """
        Handle an error by logging it and sending an appropriate message to the user.
        
        Args:
            interaction: The interaction that triggered the error
            error: The exception that was raised
            category: The category of the error
            severity: The severity of the error
            custom_message: A custom message to show to the user
            ephemeral: Whether the error message should be ephemeral
            log: Whether to log the error
        """
        # Log the error if requested
        if log:
            cls._log_error(error, category, severity, interaction)
            
        # Create the error embed
        embed = cls._create_error_embed(error, category, severity, custom_message)
        
        # Send the error message
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        except Exception as e:
            # If we can't respond to the interaction, log this as well
            logger.error(f"Failed to send error message: {str(e)}")
            
    @classmethod
    def _log_error(
        cls,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        interaction: Optional[discord.Interaction] = None
    ):
        """Log an error with appropriate context."""
        # Create error context
        error_context = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category.value,
            "severity": severity.value,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        # Add interaction details if available
        if interaction:
            error_context.update({
                "user_id": str(interaction.user.id),
                "user_name": str(interaction.user),
                "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
                "channel_id": str(interaction.channel_id) if interaction.channel_id else None,
                "command": interaction.command.name if interaction.command else None
            })
            
        # Format the log message
        log_message = (
            f"Error: {error_context['error_type']}: {error_context['error_message']}\n"
            f"Category: {error_context['category']}, Severity: {error_context['severity']}\n"
        )
        
        if interaction:
            log_message += (
                f"User: {error_context['user_name']} ({error_context['user_id']})\n"
                f"Guild: {error_context['guild_id']}, Channel: {error_context['channel_id']}\n"
                f"Command: {error_context['command']}\n"
            )
            
        # Add traceback
        log_message += f"\nTraceback:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}"
        
        # Log based on severity
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
    @classmethod
    def _create_error_embed(
        cls,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        custom_message: Optional[str] = None
    ) -> discord.Embed:
        """Create an error embed to display to the user."""
        # Get the appropriate message
        message = custom_message or cls.ERROR_MESSAGES.get(category, cls.ERROR_MESSAGES[ErrorCategory.UNKNOWN])
        
        # Create the embed
        embed = discord.Embed(
            title="Error",
            description=message,
            color=cls.SEVERITY_COLORS.get(severity, discord.Color.red())
        )
        
        # Add error details for higher severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            embed.add_field(name="Error Type", value=type(error).__name__, inline=True)
            embed.add_field(name="Error Message", value=str(error)[:1024], inline=True)
            
        # Add footer based on severity
        if severity == ErrorSeverity.CRITICAL:
            embed.set_footer(text="A critical error has occurred. Please report this to the bot administrators.")
        elif severity == ErrorSeverity.HIGH:
            embed.set_footer(text="A serious error has occurred. This has been logged for review.")
        
        return embed

class CommandErrorHandler(commands.Cog):
    """Cog for handling command errors across the bot."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors from traditional commands."""
        # Different error types need different handling
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
            
        elif isinstance(error, commands.MissingRequiredArgument):
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.LOW,
                custom_message=f"Missing required argument: `{error.param.name}`"
            )
            
        elif isinstance(error, commands.BadArgument):
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.LOW,
                custom_message="Invalid argument provided."
            )
            
        elif isinstance(error, commands.MissingPermissions):
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.MEDIUM,
                custom_message="You don't have permission to use this command."
            )
            
        elif isinstance(error, commands.BotMissingPermissions):
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                custom_message="I don't have permission to execute this command."
            )
            
        elif isinstance(error, commands.CommandOnCooldown):
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.LOW,
                custom_message=f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            )
            
        else:
            # For all other errors, use the general handler
            await ErrorHandler.handle_error(
                ctx.interaction if hasattr(ctx, 'interaction') else ctx,
                error,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM
            )
            
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors from slash commands."""
        # Handle specific error types
        if isinstance(error, app_commands.CommandOnCooldown):
            await ErrorHandler.handle_error(
                interaction,
                error,
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.LOW,
                custom_message=f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
            )
            
        elif isinstance(error, app_commands.MissingPermissions):
            await ErrorHandler.handle_error(
                interaction,
                error,
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.MEDIUM,
                custom_message="You don't have permission to use this command."
            )
            
        elif isinstance(error, app_commands.BotMissingPermissions):
            await ErrorHandler.handle_error(
                interaction,
                error,
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                custom_message="I don't have permission to execute this command."
            )
            
        elif isinstance(error, app_commands.TransformerError):
            await ErrorHandler.handle_error(
                interaction,
                error,
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.LOW,
                custom_message="Invalid argument provided."
            )
            
        else:
            # For all other errors, use the general handler
            await ErrorHandler.handle_error(
                interaction,
                error,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM
            )

async def setup(bot: commands.Bot):
    """Add the error handler cog to the bot."""
    await bot.add_cog(CommandErrorHandler(bot))
