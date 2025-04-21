# Veramon UI Components

This directory contains all UI components used in the Veramon Reunited Discord bot.

## Directory Structure

### Core UI Components
- **components.py** - Base UI components and common elements
- **modals.py** - Discord modal dialog implementations
- **pagination.py** - Pagination components for multi-page displays
- **theme.py** - UI theme definitions and styles
- **ui_registry.py** - Central registry for UI component management

### Functional UI Systems
- **battle_ui.py** - Core battle interface components
- **battle_ui_enhanced.py** - Extended battle UI with additional features
- **battle_ui_integration.py** - Integration between battle system and UI
- **trade_ui.py** - Core trading interface components
- **trading_ui_enhanced.py** - Extended trading UI with additional features
- **trading_ui_integration.py** - Integration between trading system and UI
- **menu_ui.py** - Main menu and navigation components
- **settings_ui.py** - User settings interface components

### Accessibility Features
- **accessibility.py** - Accessibility features and support
- **accessibility_ui.py** - Accessible UI components and helpers
- **accessibility_shortcuts.py** - Keyboard shortcuts and commands

## UI Component Naming Conventions

- **Base components**: `<feature>_ui.py` (e.g., battle_ui.py)
- **Enhanced components**: `<feature>_ui_enhanced.py` (e.g., battle_ui_enhanced.py)
- **System Integration**: `<feature>_ui_integration.py` (e.g., battle_ui_integration.py)

The enhanced versions extend the base components with additional features, while the integration files connect the UI with the underlying models and business logic.
