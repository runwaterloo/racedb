"""
Tests for racedbapp.shared.instrumented_cache.
"""

import pytest
from prometheus_client import REGISTRY

from racedbapp.shared.instrumented_cache import (
    InstrumentedLocMemCache,
    django_cache_get,
    django_cache_op,
)


@pytest.fixture()
def cache():
    c = InstrumentedLocMemCache("instrumented-test", {})
    c.clear()
    return c


def counter_value(metric, labels):
    """Current value of a counter sample; 0 if the label combination has not been seen."""
    try:
        return metric.labels(**labels)._value.get()
    except ValueError:
        # label combination never used yet -> no child exists -> 0
        return 0.0


def test_view_label_from_key_prefix():
    assert InstrumentedLocMemCache._view_label("index.0") == "index"
    assert InstrumentedLocMemCache._view_label("event.2026.slug.8-mi") == "event"
    assert InstrumentedLocMemCache._view_label(None) == "none"
    assert InstrumentedLocMemCache._view_label("") == "none"


def test_view_label_is_truncated():
    long_key = "x" * 100 + ".suffix"
    assert len(InstrumentedLocMemCache._view_label(long_key)) == 40


def test_get_miss_is_counted(cache):
    before = counter_value(django_cache_get, {"view": "index", "result": "miss"})
    assert cache.get("index.0") is None
    after = counter_value(django_cache_get, {"view": "index", "result": "miss"})
    assert after == before + 1


def test_get_hit_is_counted(cache):
    cache.set("index.0", "html")
    before = counter_value(django_cache_get, {"view": "index", "result": "hit"})
    assert cache.get("index.0") == "html"
    after = counter_value(django_cache_get, {"view": "index", "result": "hit"})
    assert after == before + 1


def test_set_add_delete_are_counted(cache):
    before = counter_value(django_cache_op, {"view": "index", "operation": "set"})
    cache.set("index.0", "html")
    assert counter_value(django_cache_op, {"view": "index", "operation": "set"}) == before + 1
    before = counter_value(django_cache_op, {"view": "index", "operation": "add"})
    assert cache.add("index.1", "html") is True
    assert counter_value(django_cache_op, {"view": "index", "operation": "add"}) == before + 1
    before = counter_value(django_cache_op, {"view": "index", "operation": "delete"})
    cache.delete("index.0")
    assert counter_value(django_cache_op, {"view": "index", "operation": "delete"}) == before + 1


def test_clear_is_counted_under_all(cache):
    before = counter_value(django_cache_op, {"view": "all", "operation": "clear"})
    cache.clear()
    assert counter_value(django_cache_op, {"view": "all", "operation": "clear"}) == before + 1


def test_values_round_trip(cache):
    cache.set("event.2026.slug", {"html": "<b>results</b>"})
    assert cache.get("event.2026.slug") == {"html": "<b>results</b>"}


def test_registries_only_add_expected_metrics():
    """The mixin must not register anything beyond the two declared counters."""
    names = [m.name for m in REGISTRY.collect()]
    cache_metrics = [n for n in names if n.startswith("django_cache")]
    assert set(cache_metrics) == {"django_cache_get", "django_cache_op"}
