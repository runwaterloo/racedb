#!/bin/bash
export ALLOY_VERSION=`cat ./ALLOY_VERSION | head -n 1`
export KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade alloy grafana/alloy --version $ALLOY_VERSION --values values.yaml --install --wait --timeout 5m
