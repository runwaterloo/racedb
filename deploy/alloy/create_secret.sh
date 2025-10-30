#!/bin/bash
kubectl create secret generic alloy-secrets \
 --from-literal=LOKI_USERNAME=${LOKI_USERNAME} \
 --from-literal=PROM_USERNAME=${PROM_USERNAME} \
 --from-literal=GRAFANA_API_TOKEN=${GRAFANA_API_TOKEN} \
