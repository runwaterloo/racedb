Most of the configmap is from here: https://grafana.com/docs/alloy/latest/collect/logs-in-kubernetes/

Traces: apps export OTLP/HTTP to the alloy-otlp service on port 4318
(/v1/traces). Alloy forwards to Grafana Cloud Tempo over OTLP gRPC on
443 (the tempo host has no OTLP HTTP paths).

Auth credentials come from the alloy-secrets secret:
- GRAFANA_API_TOKEN: cloud access-policy token with traces:write
- TEMPO_USERNAME: the Tempo instance ID (tenant). NOTE: Tempo is a
  separate Grafana Cloud instance from metrics/logs - its tenant ID is
  NOT the PROM_USERNAME value; using that fails with Unauthenticated.

Set the tempo endpoint in values.yaml as shown in the Grafana Cloud
portal (stack -> Tempo -> Send Traces).
