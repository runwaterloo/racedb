#!/bin/bash
# refresh the dev database with prod
set -eu

# Name of the database and role
DEV_DB_NAME="racedbdev"

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
