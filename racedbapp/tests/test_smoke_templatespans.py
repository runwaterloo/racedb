import os

import pytest
from django.test import Client


@pytest.mark.skipif(os.getenv("TRACING") != "on", reason="requires TRACING=on")
@pytest.mark.django_db
def test_template_spans_emitted(create_event, create_result):
    from opentelemetry import trace
    provider = trace.get_tracer_provider()
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

    class Grab(SpanExporter):
        spans = []

        def export(self, spans):
            Grab.spans.extend(spans)
            return SpanExportResult.SUCCESS

    provider.add_span_processor(SimpleSpanProcessor(Grab()))
    event = create_event()
    create_result(event=event)
    client = Client()
    r = client.get(f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/")
    assert r.status_code == 200
    names = [s.name for s in Grab.spans if s.name.startswith("template:")]
    print(f"\n{len(Grab.spans)} spans total, {len(names)} template spans:")
    for n in dict.fromkeys(names):
        print("  ", n)
    assert names, "no template spans emitted"
