"""OpenTelemetry span exporters for the tracing spike (PR #447 follow-up).

ChromeTraceFileExporter writes spans as Chrome Trace Event JSON, one file
per request (per trace_id), so ui.perfetto.dev opens a single clean
waterfall per page load. Used for local dev (SETTINGS=min) so traces can
be inspected without running Tempo (which is a qa/prod concern).
"""

import json
import logging
import os
from datetime import datetime, timezone

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
    """Write one Chrome Trace JSON file per request (trace_id).

    Batches can contain spans from several requests, so spans are grouped
    by trace_id and each group is written to its own file:
    .traces/<HHMMSS>-<trace_id[:8]>.json — sortable by time, drag one
    onto ui.perfetto.dev for that page load's waterfall.
    """

    def __init__(self, directory):
        self.directory = directory
        self._events = {}  # trace_id -> list of events
        os.makedirs(self.directory, exist_ok=True)

    def export(self, spans):
        try:
            for s in spans:
                if not (s.start_time and s.end_time):
                    continue
                trace_id = format(s.get_span_context().trace_id, "032x")
                self._events.setdefault(trace_id, []).append(self._event(s))
            self._flush()
            return SpanExportResult.SUCCESS
        except Exception:
            logger.exception("trace file export failed")
            return SpanExportResult.FAILURE

    def _flush(self):
        for trace_id, events in list(self._events.items()):
            ts = min(e["ts"] for e in events)
            stamp = datetime.fromtimestamp(ts / 1_000_000, timezone.utc)
            name = stamp.strftime("%H%M%S") + "-" + trace_id[:8] + ".json"
            path = os.path.join(self.directory, name)
            with open(path, "w") as f:
                json.dump({"traceEvents": events}, f)

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
