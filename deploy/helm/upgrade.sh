#!/bin/bash

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <deployment> <values-file> <tag>"
    exit 1
fi

DEPLOYMENT="$1"
VALUES_FILE="$2"
TAG="$3"

KUBECONFIG=/etc/rancher/k3s/k3s.yaml

helm upgrade --install "$DEPLOYMENT" . \
    --values "$VALUES_FILE" \
    --set image.tag="$TAG" \
    --wait --timeout 10m;
