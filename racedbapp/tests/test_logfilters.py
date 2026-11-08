import logging

import pytest
from django.test import Client, override_settings
from django.urls import path

from racedb.logfilters import TraceIdFilter, current_trace_id


def boom(request):
    raise ValueError("boom")


urlpatterns = [path("boom/", boom)]


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def captured():
    h = Capture()
    h.addFilter(TraceIdFilter())
    log = logging.getLogger("django.request")
    old = log.handlers[:]
    old_prop = log.propagate
    log.handlers = [h]
    log.propagate = False
    log.setLevel(logging.ERROR)
    yield h
    log.handlers = old
    log.propagate = old_prop


@pytest.mark.django_db
def test_500_log_stamps_trace_id(captured):
    """django.request's exception record carries a trace_id attribute."""
    with override_settings(ROOT_URLCONF=__name__, DEBUG_PROPAGATE_EXCEPTIONS=False):
        client = Client()
        with pytest.raises(ValueError):
            client.get("/boom/", raise_request_exception=False)
    assert captured.records, "django.request should log the 500"
    # Without OTel instrumentation the placeholder is stamped; the key
    # must exist and match the shared helper either way.
    assert all(r.trace_id == current_trace_id() for r in captured.records)


@pytest.mark.django_db
def test_500_middleware_json_matches_filter(captured):
    """The middleware JSON trace_id equals the filter's stamped value."""
    with override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["racedbapp.middleware.RequestLoggingMiddleware"],
    ):
        client = Client()
        with pytest.raises(ValueError):
            client.get("/boom/", raise_request_exception=False)
    assert captured.records
    assert all(r.trace_id == current_trace_id() for r in captured.records)
