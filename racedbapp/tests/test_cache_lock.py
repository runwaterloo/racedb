import time

import pytest
from django.core.cache import cache

from racedbapp.shared import cache_lock


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def unique_key():
    return "test_cache_lock_index"


def make_render_func(calls, result="html", delay=0):
    def render_func():
        calls.append(time.monotonic())
        if delay:
            time.sleep(delay)
        if isinstance(result, Exception):
            raise result
        return result

    return render_func


class TestGetOrRender:
    def test_returns_cached_value_without_rendering(self, unique_key):
        cache_lock.set(unique_key, "cached_html")
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls))
        assert result == "cached_html"
        assert calls == []

    def test_renders_and_caches_when_missing(self, unique_key):
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "html1"))
        assert result == "html1"
        assert cache_lock.get(unique_key) == "html1"
        # second call must be served from cache, not re-rendered
        result2 = cache_lock.get_or_render(unique_key, make_render_func(calls, "html2"))
        assert result2 == "html1"
        assert len(calls) == 1

    def test_set_stores_value(self, unique_key):
        cache_lock.set(unique_key, "value")
        assert cache.get(unique_key) == "value"

    def test_caches_failure_key_is_not_left_behind_on_error(self, unique_key):
        def failing():
            raise RuntimeError("render failed")

        with pytest.raises(RuntimeError):
            cache_lock.get_or_render(unique_key, failing)
        # a subsequent call re-renders rather than serving an error
        result = cache_lock.get_or_render(unique_key, make_render_func([], "fresh"))
        assert result == "fresh"


class TestClear:
    def test_clear_invalidates_entries(self, unique_key):
        cache_lock.set(unique_key, "old_html")
        assert cache_lock.get(unique_key) == "old_html"
        cache_lock.clear(source="test")
        assert cache_lock.get(unique_key) is None

    def test_clear_requires_source(self):
        with pytest.raises(TypeError):
            cache_lock.clear()

    def test_clear_rejects_empty_source(self):
        with pytest.raises(ValueError):
            cache_lock.clear("")
        with pytest.raises(ValueError):
            cache_lock.clear(None)


@pytest.mark.django_db
def test_index_view_renders_once_and_caches(
    monkeypatch, create_category, create_event, create_result
):
    from rest_framework.test import APIClient

    from racedbapp import view_index

    event = create_event()
    category = create_category(name_suffix="a")
    create_result(event=event, gender="F", category=category, place=1)
    create_result(event=event, gender="F", category=category, place=3)
    create_result(event=event, gender="F", category=category, place=5)
    create_result(event=event, gender="M", category=category, place=2)
    create_result(event=event, gender="M", category=category, place=4)
    create_result(event=event, gender="M", category=category, place=6)
    render_count = []
    original_render_index = view_index._render_index

    def counting_render(request):
        render_count.append(1)
        return original_render_index(request)

    monkeypatch.setattr(view_index, "_render_index", counting_render)
    client = APIClient()
    response1 = client.get("/")
    response2 = client.get("/")
    assert response1.status_code == 200
    assert response2.status_code == 200
    # When the debug toolbar is enabled it appends per-request content
    # (data-request-id, panels) to each response AFTER the view returns,
    # so the raw bytes differ between requests even on a cache hit.
    # Compare only the page itself, before the toolbar's block.
    marker = b'<div id="djDebug"'
    assert response2.content.split(marker)[0] == response1.content.split(marker)[0]
    assert len(render_count) == 1
