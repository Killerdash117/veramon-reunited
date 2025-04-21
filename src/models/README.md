# Veramon Models

This directory contains the core data models and business logic for the Veramon Reunited bot.

## Directory Contents

- **battle.py** - Core battle system model that handles turn-based combat logic
- **battle_actor.py** - Battle participant actor model for battle participants
- **battle_mechanics.py** - Implementation of battle mechanics, damage calculation and effects
- **battle_manager.py** - Manages active battles and matchmaking
- **event.py** - Event system model for game events
- **event_manager.py** - Manages scheduled and triggered events
- **field_conditions.py** - Battle field conditions and environmental effects
- **models.py** - Base models and shared functionality
- **permissions.py** - User permission models and role-based access control
- **quest.py** - Quest system model for player quests and objectives
- **quest_manager.py** - Manages active quests and progress tracking
- **status_effects.py** - Battle status effects implementation (buffs, debuffs)
- **trade.py** - Trading system model for player-to-player item exchanges
- **veramon.py** - Core Veramon entity model with stats and abilities

## Key Models

### Battle System

The battle system is comprised of multiple files that work together:
- `battle.py` - Main battle class and state management
- `battle_actor.py` - Battle participants
- `battle_mechanics.py` - Game mechanics implementation

### Trading System

The trading system provides a complete infrastructure for player trades:
- `trade.py` - Core trading functionality with safety features

### Quest System

The quest system manages player activities and objectives:
- `quest.py` - Quest definitions and progress tracking
- `quest_manager.py` - Quest lifecycle management
