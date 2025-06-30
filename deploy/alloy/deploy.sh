#!/bin/bash
export ALLOY_CHART_VERSION=`cat ./ALLOY_CHART_VERSION | head -n 1`
export KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade alloy grafana/alloy --version $ALLOY_CHART_VERSION --values values.yaml --install --wait --timeout 5m
