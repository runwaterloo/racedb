"""Shared logging helpers for trace-id correlation.

Stamps the current OTel trace_id onto every log record passing through a
handler, so the verbose console format can carry [trace_id=...] on all
Django logs (django.request 500s, security warnings, etc.) and join them
to the middleware JSON line and Tempo traces.
"""

from opentelemetry import trace

TRACE_ID_PLACEHOLDER = "-"


def current_trace_id() -> str:
    """32-hex current trace id, or '-' when there is no valid span."""
    span = trace.get_current_span()
    sc = span.get_span_context() if span else None
    if sc and sc.is_valid:
        return f"{sc.trace_id:032x}"
    return TRACE_ID_PLACEHOLDER


class TraceIdFilter:
    """logging.Filter that adds a `trace_id` attribute to each record."""

    def filter(self, record):
        record.trace_id = current_trace_id()
        return True
