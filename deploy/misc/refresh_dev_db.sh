#!/bin/bash
# refresh the dev database with prod
set -eu

# Name of the database and role
DEV_DB_NAME="racedbdev"

# Password for dev role
DEV_PASSWORD=$(grep DB_PASSWORD /srv/racedb_secrets_dev/secrets.py | awk -F"'" '{print $2}')

# Check if the role exists
ROLE_EXISTS=$(kubectl exec -i postgres-0 -- psql -U racedb -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DEV_DB_NAME';")

# If it doesn't exist, create it
if [ "$ROLE_EXISTS" != "1" ]; then
    echo "Role $DEV_DB_NAME does not exist. Creating..."
        kubectl exec -i postgres-0 -- psql -U racedb -d postgres -c "CREATE ROLE $DEV_DB_NAME WITH LOGIN PASSWORD '$DEV_PASSWORD';"
else
    echo "Role $DEV_DB_NAME already exists. Skipping creation."
fi

# Check if the database exists
DB_EXISTS=$(kubectl exec -i postgres-0 -- psql -U racedb -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DEV_DB_NAME';")

# If it doesn't exist, create it
if [ "$DB_EXISTS" != "1" ]; then
    echo "Database $DEV_DB_NAME does not exist. Creating..."
    kubectl exec -i postgres-0 -- psql -U racedb -d postgres -c "CREATE DATABASE $DEV_DB_NAME OWNER $DEV_DB_NAME;"
else
    echo "Database $DEV_DB_NAME already exists. Skipping creation."
fi

echo "Importing data from prod to dev..."
kubectl exec -i postgres-0 -- pg_dump -U racedb -d racedb --clean --if-exists --no-owner --no-acl --no-comments | kubectl exec -i postgres-0 -- psql -q -U $DEV_DB_NAME -d $DEV_DB_NAME >/dev/null
echo "Import complete."

# Clear cache in dev pod if it exists
DEV_POD=$(kubectl get pod -l "app.kubernetes.io/instance=racedbdev,app.kubernetes.io/task=web" -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || true)
if [ -n "$DEV_POD" ]; then
    echo "Clearing cache in dev pod..."
    kubectl exec -it "$DEV_POD" -- ./manage.py clear_cache
    echo "Cache cleared."
fi
