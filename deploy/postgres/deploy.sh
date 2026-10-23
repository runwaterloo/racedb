#!/bin/bash

./create_secret.sh
kubectl apply -f ./manifests
echo "Waiting for Postgres pod to be ready..."
kubectl rollout status statefulset/postgres --timeout=180s

# Enable pg_stat_statements (requires the shared_preload_libraries arg in
# statefulset.yaml, applied above, so the extension can be created on the
# restarted pod).
kubectl exec postgres-0 -- psql -U "$(kubectl get secret postgres-secret -o jsonpath='{.data.username}' | base64 -d)" -d "$(kubectl get secret postgres-secret -o jsonpath='{.data.username}' | base64 -d)" -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Let the exporter user use pg_monitor stats
kubectl exec postgres-0 -- psql -U "$(kubectl get secret postgres-secret -o jsonpath='{.data.username}' | base64 -d)" -d "$(kubectl get secret postgres-secret -o jsonpath='{.data.username}' | base64 -d)" -c "GRANT pg_monitor TO CURRENT_USER;"
