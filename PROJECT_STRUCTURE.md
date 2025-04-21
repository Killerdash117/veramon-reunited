# Veramon Reunited - Project Structure

This document provides an overview of the Veramon Reunited project structure and organization.

## Directory Structure

```
veramon_reunited/
├── data/                   # Game data files (Veramon database, items, etc.)
├── src/                    # Source code
│   ├── assets/             # Static assets (images, sounds, etc.)
│   ├── cogs/               # Discord bot command groups
│   ├── core/               # Core bot functionality
│   ├── data/               # Data loading and management
│   ├── db/                 # Database operations
│   ├── defaults/           # Default configuration
│   ├── models/             # Data models and business logic
│   ├── tools/              # Testing and maintenance tools
│   ├── ui/                 # Legacy UI components
│   ├── utils/              # Utility functions
│   │   └── ui/             # UI components
│   └── main.py             # Bot entry point
├── tests/                  # Test suite
├── .env.sample             # Environment variable template
├── CHANGELOG.md            # Version history
├── LICENSE                 # License information
├── OWNERSHIP.md            # Project ownership details
├── README.md               # Project documentation
└── requirements.txt        # Python dependencies
```

## Key Components

### Battle System

The battle system is implemented across multiple files:
- **Models**: `src/models/battle.py`, `src/models/battle_actor.py`, `src/models/battle_mechanics.py`
- **UI**: `src/utils/ui/battle_ui.py`, `src/utils/ui/battle_ui_enhanced.py`, `src/utils/ui/battle_ui_integration.py`
- **Cogs**: `src/cogs/gameplay/battle_cog.py`

### Trading System

The trading system is implemented across:
- **Models**: `src/models/trade.py`
- **UI**: `src/utils/ui/trade_ui.py`, `src/utils/ui/trading_ui_enhanced.py`, `src/utils/ui/trading_ui_integration.py`
- **Cogs**: `src/cogs/economy/trading_cog.py`

### Core Game Data

Veramon data and game mechanics are defined in:
- **Veramon Definitions**: `data/veramon_database.json`
- **Models**: `src/models/veramon.py`
- **Data Loading**: `src/utils/data_loader.py`, `src/utils/cache.py`

## Development Guidelines

For consistent development:

1. **Directory Organization**: 
   - Place files in appropriate directories based on function
   - Follow the existing module structure

2. **Naming Conventions**:
   - Use snake_case for files, variables, and functions
   - Use CamelCase for classes
   - Append `_cog.py` to Discord command cogs

3. **Code Structure**:
   - Separate UI from business logic
   - Use models for core game mechanics
   - Use utilities for shared functionality

4. **Documentation**:
   - Include docstrings for all classes and functions
   - Add README files in key directories
   - Update documentation when making significant changes
