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
