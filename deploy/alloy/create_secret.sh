#!/bin/bash
kubectl create secret generic alloy-secrets \
 --from-literal=loki-username=${LOKI_USERNAME} \
 --from-literal=prom_username=${PROM_USERNAME} \
 --from-literal=grafana-api-token=${GRAFANA_API_TOKEN} \
 --from-literal=mysql-data-source-name=${MYSQL_DATA_SOURCE_NAME}
