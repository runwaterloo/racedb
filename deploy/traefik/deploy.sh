#!/bin/bash
export TRAEFIK_CHART_VERSION=`cat ./TRAEFIK_CHART_VERSION`
mkdir -p /pv/traefik 2>/dev/null
chmod 777 /pv/traefik
kubectl apply -f pv.yaml
kubectl apply -f pvc.yaml
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm upgrade traefik traefik/traefik --version $TRAEFIK_CHART_VERSION --values values.yaml --install
