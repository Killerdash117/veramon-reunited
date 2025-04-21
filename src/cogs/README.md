# Veramon Cogs Directory

This directory contains all Discord command cogs for the Veramon Reunited bot. Each cog represents a different functional area of the bot.

## Directory Structure

### Admin Cogs
- **admin/** - Administrative commands for bot management and monitoring

### Gameplay Cogs
- **gameplay/** - Core gameplay commands including battles, exploration, and Veramon management
- **economy/** - Economy-related commands for token management and purchases
- **faction/** - Faction-based commands and team gameplay features

### User Experience Cogs
- **settings/** - User preference and settings management
- **social/** - Social interaction features
- **user/** - User profile and statistics

### Technical Cogs
- **events/** - Event handling and scheduling
- **integration/** - Integration with external services
- **moderation/** - Server moderation tools

## Cog Development Guidelines

When developing new cogs, please follow these guidelines:

1. **Organization**: Place cogs in the appropriate subdirectory based on function
2. **Initialization**: Include an `__init__.py` file in each directory
3. **Naming Convention**: Use snake_case for filenames and append `_cog` to the main cog file
4. **Documentation**: Include docstrings explaining the cog's purpose and commands
5. **Error Handling**: Implement proper error handling for all commands

## Key Cogs

### Battle System
Located in `gameplay/battle_cog.py`, this provides PvP and PvE battle functionality.

### Trading System  
Located in `economy/trading_cog.py`, this provides player-to-player trading functionality.

### Settings System
Located in `settings/settings_cog.py`, this provides user customization options.
