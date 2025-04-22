#!/bin/bash
# Veramon Reunited - Automatic Backup Script
# This script creates backups of critical bot data including battles and trades

# Configuration
BACKUP_DIR="/app/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="/app/data/veramon_reunited.db"
BATTLE_DIR="/app/battle-system-data"
TRADE_DIR="/app/trading-data"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Backup SQLite database (containing battle and trade records)
echo "Creating database backup..."
sqlite3 $DB_FILE ".backup '$BACKUP_DIR/veramon_db_$DATE.sq3'"

# Export schema and data for easy recovery
echo "Exporting schema and data..."
sqlite3 $DB_FILE ".schema" > "$BACKUP_DIR/schema_$DATE.sql"
sqlite3 $DB_FILE ".dump" > "$BACKUP_DIR/dump_$DATE.sql"

# Compress battle logs (these can be large with detailed battle logs)
echo "Backing up battle system data..."
if [ -d "$BATTLE_DIR" ]; then
    tar -czf "$BACKUP_DIR/battles_$DATE.tar.gz" -C $(dirname $BATTLE_DIR) $(basename $BATTLE_DIR) 
fi

# Compress trade history
echo "Backing up trading system data..."
if [ -d "$TRADE_DIR" ]; then
    tar -czf "$BACKUP_DIR/trades_$DATE.tar.gz" -C $(dirname $TRADE_DIR) $(basename $TRADE_DIR)
fi

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "veramon_db_*.sq3" -type f -mtime +7 -delete
find $BACKUP_DIR -name "schema_*.sql" -type f -mtime +7 -delete
find $BACKUP_DIR -name "dump_*.sql" -type f -mtime +7 -delete
find $BACKUP_DIR -name "battles_*.tar.gz" -type f -mtime +7 -delete
find $BACKUP_DIR -name "trades_*.tar.gz" -type f -mtime +7 -delete

echo "Backup completed successfully on $(date)"
