#!/bin/bash
# create dev database
set -eu

# Name of the database and role
DB_NAME=$1

# Download the latest backup from S3
aws s3 cp s3://${BUCKET}/database_backup/racedb.latest.sql.gz /tmp/racedb.latest.sql.gz

# Restore the backup into the dev database
echo "Restoring latest backup into $DB_NAME..."
gunzip -c /tmp/racedb.latest.sql.gz | kubectl exec -i postgres-0 -- psql -U $DB_NAME -d $DB_NAME --quiet >/dev/null
echo "Restore complete."

# Clean up
rm -rf /tmp/racedb.latest.sql.gz
