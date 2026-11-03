Most of the configmap is from here: https://grafana.com/docs/alloy/latest/collect/logs-in-kubernetes/

Traces: apps export OTLP/HTTP to the alloy service on port 4318
(OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4318). Alloy forwards to
Grafana Cloud Tempo using PROM_USERNAME (shared stack instance ID) +
GRAFANA_API_TOKEN from alloy-secrets. Set the real tempo endpoint in
values.yaml where marked XX after enabling Tempo in the Grafana portal.
