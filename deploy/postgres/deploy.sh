#!/bin/bash

./create_secret.sh
kubectl apply -f ./manifests
echo "Waiting for Postgres pod to be ready..."
kubectl wait --for=condition=ready pod/postgres-0 --timeout=180s
