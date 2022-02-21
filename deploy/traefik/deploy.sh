#!/bin/bash
mkdir -p /pv/traefik 2>/dev/null
chmod 777 /pv/traefik
kubectl apply -f pv.yaml
kubectl apply -f pvc.yaml
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm upgrade traefik traefik/traefik --values values.yaml --install 
