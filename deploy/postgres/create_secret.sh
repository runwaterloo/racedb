#!/bin/bash
set -e

echo "Checking if secret 'postgres-secret' already exists"
if kubectl get secret postgres-secret &> /dev/null; then
    echo "Secret 'postgres-secret' already exists. Skipping creation."
    exit 0
fi

echo "Creating 'postgres-secret'..."
POSTGRES_PASSWORD=$(grep DB_PASSWORD /srv/racedb_secrets/secrets.py | awk -F"'" '{print $2}')
POSTGRES_DEV_PASSWORD=$(grep DB_PASSWORD /srv/racedb_secrets_dev/secrets.py | awk -F"'" '{print $2}')

kubectl create secret generic postgres-secret \
  --from-literal=username="racedb" \
  --from-literal=password="$POSTGRES_PASSWORD" \
  --from-literal=dev_db="racedbdev" \
  --from-literal=dev_username="racedbdev" \
  --from-literal=dev_password="$POSTGRES_DEV_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -
