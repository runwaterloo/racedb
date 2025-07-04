#!/bin/bash

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <deployment> <values-file> <tag>"
    exit 1
fi

export DEPLOYMENT="$1"
export VALUES_FILE="$2"
export TAG="$3"

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

helm upgrade --install "$DEPLOYMENT" . \
    --values "$VALUES_FILE" \
    --set image.tag="$TAG" \
    --wait --timeout 10m;

# Run clear_cache in one of the ready web pods after upgrade
sleep 5
POD=$(kubectl get pods -l app.kubernetes.io/instance=racedb,app.kubernetes.io/name=racedb,app.kubernetes.io/task=web \
    --field-selector=status.phase=Running \
    -o jsonpath='{.items[?(@.status.containerStatuses[0].ready==true)].metadata.name}' | awk '{print $1}')
if [ -n "$POD" ]; then
    echo "Running python manage.py clear_cache in pod $POD"
    kubectl exec "$POD" -- python manage.py clear_cache
else
    echo "No matching ready pod found to run clear_cache."
fi
