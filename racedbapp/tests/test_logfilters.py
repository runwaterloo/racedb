import logging
import sys
import types

import pytest
from django.test import Client, override_settings
from django.urls import path

from racedb.logfilters import TraceIdFilter, current_trace_id


def _fake_span(valid=True, trace_id=0x46CB0D19A1B2C3D4E5F60718293A4B5C):
    sc = types.SimpleNamespace(is_valid=valid, trace_id=trace_id)
    return types.SimpleNamespace(get_span_context=lambda: sc)


def test_current_trace_id_formats_32_hex(monkeypatch):
    monkeypatch.setattr(
        "racedb.logfilters.trace.get_current_span", lambda: _fake_span()
    )
    assert current_trace_id() == "46cb0d19a1b2c3d4e5f60718293a4b5c"


def test_current_trace_id_dash_without_span(monkeypatch):
    monkeypatch.setattr(
        "racedb.logfilters.trace.get_current_span", lambda: _fake_span(valid=False)
    )
    assert current_trace_id() == "-"


def test_filter_stamps_record(monkeypatch):
    monkeypatch.setattr(
        "racedb.logfilters.trace.get_current_span", lambda: _fake_span()
    )
    record = logging.LogRecord("django.request", logging.ERROR, __file__, 1, "x", None, None)
    assert TraceIdFilter().filter(record) is True
    assert record.trace_id == "46cb0d19a1b2c3d4e5f60718293a4b5c"


# --- Django's own error log line picks up the active span -------------------

def _boom(request):
    raise ValueError("boom")


urlpatterns = [path("boom/", _boom)]


@pytest.fixture
def dev_logging(monkeypatch):
    """Apply the prod/dev LOGGING config the way settings.py builds it."""
    import importlib.util
    import os

    monkeypatch.setenv("SETTINGS", "dev")
    monkeypatch.setattr(sys, "modules", {**sys.modules})
    spec = importlib.util.spec_from_file_location(
        "_racedb_settings_dev", "racedb/settings/settings.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = mod.LOGGING
    monkeypatch.undo()
    assert os.getenv("SETTINGS") != "dev"
    return cfg


@pytest.mark.django_db
def test_request_exception_log_carries_trace_id(dev_logging, monkeypatch):
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    tracer = provider.get_tracer("test")

    # Build the real handler/formatter stack from the dev config.
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(dev_logging["formatters"]["verbose"]["format"]))
    handler.addFilter(TraceIdFilter())
    django_logger = logging.getLogger("django.request")
    old_handlers = django_logger.handlers[:]
    django_logger.handlers = [handler]
    django_logger.addFilter(lambda r: True)

    captured = []
    monkeypatch.setattr(
        handler, "emit", lambda record: captured.append(record)
    )

    client = Client(raise_request_exception=False)
    try:
        with override_settings(ROOT_URLCONF=__name__):
            with tracer.start_as_current_span("request-span") as span:
                expected = f"{span.get_span_context().trace_id:032x}"
                client.get("/boom/")
    finally:
        django_logger.handlers = old_handlers

    errors = [r for r in captured if r.levelno >= logging.ERROR]
    assert errors, "Django did not log the exception"
    record = errors[0]
    assert record.name == "django.request"
    assert record.exc_info is not None
    assert record.trace_id == expected
    # The formatted line is what lands in Loki: trace_id in front of the message.
    line = handler.formatter.format(record)
    assert f"trace_id={expected}" in line
    assert "Internal Server Error: /boom/" in line
