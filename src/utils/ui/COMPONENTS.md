# Veramon UI Component Architecture

This document explains the structure and relationship between the different UI components in the Veramon Reunited bot.

## UI Component Hierarchy

Veramon uses a 3-tier UI component architecture:

1. **Base Components** (`<feature>_ui.py`)
   - Core functionality 
   - Minimal dependencies
   - Used for lightweight interactions

2. **Enhanced Components** (`<feature>_ui_enhanced.py`)
   - Extends base components with advanced features
   - More visually rich
   - May have additional dependencies

3. **Integration Components** (`<feature>_ui_integration.py`)
   - Connects UI components to backend systems
   - Handles data flow between UI and models
   - Implements business logic for UI actions

## Battle UI Components

- **battle_ui.py**: Core battle UI with basic move selection and Veramon switching
- **battle_ui_enhanced.py**: Enhanced battle UI with animations, detailed stats, and extended functionality
- **battle_ui_integration.py**: Connects battle UI to battle model system

## Trade UI Components

- **trade_ui.py**: Core trading UI for basic item selection and trade confirmation
- **trading_ui_enhanced.py**: Enhanced trading UI with item previews, comparison, and additional safety features
- **trading_ui_integration.py**: Connects trading UI to trading system models

## Menu UI Components

- **menu_ui.py**: Core menu system for main navigation and basic interaction

## Using the Appropriate Component

- For minimal resource usage, use base components
- For rich user experience, use enhanced components
- For full system integration, use integration components

## Component Dependencies

```
Base Component (e.g., battle_ui.py)
  ↑
Enhanced Component (e.g., battle_ui_enhanced.py)
  ↑
Integration Component (e.g., battle_ui_integration.py)
```

Each tier depends on the tier below it, but not vice versa, allowing for flexible integration.
