#!/bin/bash
# Usage ./importdb.sh <path_to_sql_dump.gz>
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_sql_dump.gz>"
    exit 1
fi

echo "Dropping and recreating database..."
docker exec -i postgres psql -U racedb -d postgres -c "DROP DATABASE IF EXISTS racedb;"
docker exec -i postgres psql -U racedb -d postgres -c "CREATE DATABASE racedb OWNER racedb;"

echo "Importing data..."
gunzip -c "$1" | docker exec -i postgres psql -U racedb -d racedb --quiet > /dev/null
echo "Import complete."
