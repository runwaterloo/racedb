"""Shared OpenTelemetry tracer for custom spans.

Uses the OTel API only: when TRACING=off no provider is registered, so
get_tracer() returns a no-op tracer and every context manager below is a
cheap passthrough. When TRACING=on the real provider is installed and
spans land in Tempo, nested under whatever span is active at the call
site (view spans from DjangoInstrumentor, or custom spans).
"""

from opentelemetry import trace

tracer = trace.get_tracer("racedbapp")
