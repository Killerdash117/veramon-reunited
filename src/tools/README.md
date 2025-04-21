# Veramon Tools

This directory contains maintenance, testing, and utility tools for the Veramon Reunited bot.

## Testing Tools

- **test_veramon_bot.py** - Comprehensive test suite for the Veramon bot
- **test_veramon_loading.py** - Tests for Veramon data loading and caching
- **test_veramon_full.py** - Full integration tests for all systems
- **security_test.py** - Security validation and vulnerability testing

## Data Management Tools

- **fix_data_structure.py** - Repairs and validates Veramon data structures
- **fix_database_indices.py** - Adds and optimizes database indices
- **maintain_veramon_database.py** - Database maintenance utilities
- **merge_veramon_data.py** - Merges Veramon data from multiple sources
- **rename_veramon_file.py** - Renames and updates Veramon data files
- **remove_redundant_data.py** - Identifies and removes redundant data
- **validate_veramon_data.py** - Validates Veramon data integrity

## Backup Tools

The **backup_scripts** directory contains tools for backing up and restoring data.

## Data Fixes

The **data_fixes** directory contains tools for fixing specific data issues.

## Usage

Most tools can be run from the command line with Python:

```
python -m src.tools.tool_name
```

For example:

```
python -m src.tools.test_veramon_full
```

Some tools may require additional arguments. Run with `--help` for more information.

## Adding New Tools

When adding new tools, follow these conventions:
1. Use descriptive names with snake_case
2. Add comprehensive documentation
3. Include command-line argument parsing
4. Add error handling and logging
