#!/bin/bash
export TRAEFIK_CHART_VERSION=`cat ./TRAEFIK_CHART_VERSION`
mkdir -p /pv/traefik 2>/dev/null
chmod 777 /pv/traefik
kubectl apply -f pv.yaml
kubectl apply -f pvc.yaml
kubectl get secret grafana-secrets >/dev/null 2>&1 || kubectl create secret generic grafana-secrets \
  --from-literal=username="$GRAFANA_USERNAME" \
  --from-literal=api_key="$GRAFANA_API_KEY"
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm upgrade traefik traefik/traefik --version $TRAEFIK_CHART_VERSION --values values.yaml --install
