"""Logging filters that link log lines back to their trace.

Loki and Tempo are joined on trace_id. The request middleware emits it in
its JSON line, but Django logs its own lines (the unhandled-exception
traceback, django.security.*, DB errors) through the "django" logger,
which knows nothing about the current span. A handler filter stamps the
trace_id on every record passing through, so those lines carry it too.
"""

import logging

from opentelemetry import trace


def current_trace_id():
    """The active span's trace_id as 32 hex chars, or "-" when no span."""
    span = trace.get_current_span()
    sc = span.get_span_context() if span else None
    if sc and sc.is_valid:
        return f"{sc.trace_id:032x}"
    return "-"


class TraceIdFilter(logging.Filter):
    """Stamp record.trace_id; the "verbose" formatter prints it."""

    def filter(self, record):
        record.trace_id = current_trace_id()
        return True
