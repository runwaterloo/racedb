#!/bin/bash
export ALLOY_VERSION=`cat ./ALLOY_VERSION | head -n 1`
export KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
sed -i "s/LOKI_USERNAME/${LOKI_USERNAME}/g" values.yaml
sed -i "s/PROM_USERNAME/${PROM_USERNAME}/g" values.yaml
sed -i "s/GRAFANA_API_TOKEN/${GRAFANA_API_TOKEN}/g" values.yaml
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade alloy grafana/alloy --version $ALLOY_VERSION --values values.yaml --install
