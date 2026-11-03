"""OpenTelemetry span exporters for the tracing spike (PR #447 follow-up).

ChromeTraceFileExporter writes spans as Chrome Trace Event JSON, which
ui.perfetto.dev opens natively via drag-and-drop. Used for local dev
(SETTINGS=min) so traces can be inspected without running Tempo.
"""

import json
import logging
import os

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)

_NANO = 1000  # ns -> us


def _attributes(attrs):
    if not attrs:
        return {}
    return {
        k: v.value if hasattr(v, "value") else v for k, v in attrs.items()
    }


class ChromeTraceFileExporter(SpanExporter):
    """Write spans to a JSON file in Chrome Trace Event format.

    The file is a complete {"traceEvents": [...]} document, rewritten on
    every batch, so ui.perfetto.dev opens it at any point mid-run.
    """

    def __init__(self, path):
        self.path = path
        self._events = []
        # Truncate on startup so a new run starts a fresh trace file.
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._flush_file()

    def export(self, spans):
        try:
            self._events.extend(
                self._event(s) for s in spans if s.start_time and s.end_time
            )
            self._flush_file()
            return SpanExportResult.SUCCESS
        except Exception:
            logger.exception("trace file export failed")
            return SpanExportResult.FAILURE

    def _flush_file(self):
        with open(self.path, "w") as f:
            json.dump({"traceEvents": self._events}, f)

    def _event(self, span: ReadableSpan):
        ctx = span.get_span_context()
        return {
            "name": span.name,
            "cat": "trace",
            "ph": "X",
            "ts": span.start_time // _NANO,
            "dur": (span.end_time - span.start_time) // _NANO,
            "pid": span.resource.attributes.get("service.name", "racedb"),
            "tid": 0,
            "args": {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
                "parent_span_id": format(span.parent.span_id, "016x")
                if span.parent
                else None,
                "attributes": _attributes(span.attributes),
                "status": span.status.status_code.name,
            },
        }
