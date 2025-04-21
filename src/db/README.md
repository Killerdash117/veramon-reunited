# Veramon Database Module

This directory contains the database management code for Veramon Reunited.

## Core Components

- **db.py** - Core database connection management and pooling
- **db_manager.py** - High-level database operations and query interface
- **cache_manager.py** - Caching system for database operations
- **faction_economy_db.py** - Faction-specific economy database operations
- **faction_economy_security_tables.py** - Security tables for faction economy

## Schema

The database schema is maintained in the `schema_updates` directory, which contains:
- **schema_updates/** - SQL scripts for database migrations and schema evolution

## Database Design

The Veramon database uses SQLite and includes tables for:

1. **Users** - Player information and statistics
2. **Veramon** - Veramon data including stats and abilities
3. **Captures** - Player's captured Veramon
4. **Battles** - Battle records and statistics
5. **Trades** - Trading records and history
6. **Items** - Item definitions and inventory
7. **Quests** - Quest definitions and progress tracking
8. **Factions** - Faction data and membership

## Performance Optimizations

The database is optimized with:
- Connection pooling for efficient connection management
- Prepared statements for query performance
- Indices on frequently queried columns
- Caching for commonly accessed data

## Usage Guidelines

When working with the database:
1. Always use parameterized queries to prevent SQL injection
2. Release database connections after use
3. Use transactions for multi-step operations
4. Consider adding indices for frequently queried columns
5. Use the cache_manager for read-heavy operations
