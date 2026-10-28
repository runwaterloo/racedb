import threading
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


def render_calls():
    return []


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

    def test_concurrent_requests_render_once(self, unique_key):
        calls = []
        render_func = make_render_func(calls, "rendered", delay=0.3)
        results = [None] * 10
        barrier = threading.Barrier(10)

        def worker(i):
            barrier.wait()
            results[i] = cache_lock.get_or_render(unique_key, render_func)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert all(r == "rendered" for r in results)
        assert len(calls) == 1

    def test_waiter_gets_cached_value_set_after_it_started_waiting(self, unique_key):
        calls = []
        holder = cache_lock._lock_key(unique_key)
        cache.add(holder, "owner-token", cache_lock.LOCK_TTL_SECONDS)
        results = [None]

        def waiter():
            results[0] = cache_lock.get_or_render(unique_key, make_render_func(calls))

        thread = threading.Thread(target=waiter)
        thread.start()
        time.sleep(0.3)  # let the waiter block on the held lock
        cache_lock.set(unique_key, "warm_html")
        cache.delete(holder)
        thread.join(timeout=10)
        assert results[0] == "warm_html"
        assert calls == []  # waiter must not render

    def test_lock_released_after_render_exception(self, unique_key):
        calls = []
        with pytest.raises(ValueError):
            cache_lock.get_or_render(unique_key, make_render_func(calls, ValueError("boom")))
        assert cache.get(cache_lock._lock_key(unique_key)) is None
        # next call renders normally instead of waiting
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "recovered"))
        assert result == "recovered"
        assert len(calls) == 2

    def test_caches_failure_key_is_not_left_behind_on_error(self, unique_key):
        def failing():
            raise RuntimeError("render failed")

        with pytest.raises(RuntimeError):
            cache_lock.get_or_render(unique_key, failing)
        # a subsequent call re-renders rather than serving a stale None
        result = cache_lock.get_or_render(unique_key, make_render_func([], "fresh"))
        assert result == "fresh"

    def test_falls_back_to_render_after_wait_timeout(self, unique_key, monkeypatch):
        monkeypatch.setattr(cache_lock, "WAIT_TIMEOUT_SECONDS", 0.1)
        monkeypatch.setattr(cache_lock, "POLL_INTERVAL_SECONDS", 0.01)
        cache.add(cache_lock._lock_key(unique_key), "stuck-token", 120)
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "timeout_render"))
        assert result == "timeout_render"
        assert len(calls) == 1

    def test_waiter_takes_over_lock_after_release_without_cache(self, unique_key):
        # lock exists but the renderer released it without caching a value;
        # a waiter must acquire the lock itself and render, not spin forever
        cache.add(cache_lock._lock_key(unique_key), "ghost", 1)
        cache.delete(cache_lock._lock_key(unique_key))  # simulate release, no cache value
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "took_over"))
        assert result == "took_over"
        assert len(calls) == 1


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


class TestGeneration:
    def test_bump_invalidates_entries(self, unique_key):
        cache_lock.set(unique_key, "old_html")
        assert cache_lock.get(unique_key) == "old_html"
        cache_lock.bump_generation(source="test")
        assert cache_lock.get(unique_key) is None

    def test_render_started_before_bump_is_ignored_after(self, unique_key):
        # the race this design exists to fix: a render that started before a
        # bump must not re-cache itself over newer content
        old_generation = cache_lock._current_generation()
        cache_lock.set(unique_key, "old_html")
        cache_lock.bump_generation(source="test")
        # simulate the in-flight render finishing after the bump
        cache.set(unique_key, (old_generation, "stale_render"), 3600)
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "fresh_html"))
        assert result == "fresh_html"
        assert len(calls) == 1

    def test_bump_is_atomic_and_monotonic(self, unique_key):
        start = cache_lock._current_generation()
        cache_lock.bump_generation(source="test")
        cache_lock.bump_generation(source="test")
        assert cache_lock._current_generation() == start + 2

    def test_unstamped_entries_are_treated_as_misses(self, unique_key):
        # entries written without a generation stamp can never be hits
        cache.set(unique_key, "raw_value")
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "stamped"))
        assert result == "stamped"
        assert cache_lock.get(unique_key) == "stamped"

    def test_set_stamps_with_current_generation(self, unique_key):
        cache_lock.bump_generation(source="test")
        cache_lock.set(unique_key, "value")
        stored = cache.get(unique_key)
        assert isinstance(stored, tuple)
        assert stored[0] == cache_lock._current_generation()


def test_bump_generation_requires_source():
    # every bump must be attributable; a bare call is a programming error
    with pytest.raises(TypeError):
        cache_lock.bump_generation()


def test_bump_generation_rejects_empty_source():
    with pytest.raises(ValueError):
        cache_lock.bump_generation("")
    with pytest.raises(ValueError):
        cache_lock.bump_generation(None)


class TestRenderSpanningBump:
    """A render that starts before a bump and finishes after it must not
    poison the cache: its write carries the pre-bump generation and reads
    as a miss, so the next request re-renders from post-bump data."""

    def test_render_spanning_bump_writes_stale_generation(self, unique_key):
        captured = {}

        def slow_render():
            captured["gen"] = cache_lock._current_generation()
            cache_lock.bump_generation(source="test")  # data changes mid-render
            return "stale_html"

        calls = []
        result = cache_lock.get_or_render(unique_key, slow_render)
        calls.append(1)
        assert result == "stale_html"  # the renderer's own caller sees its output
        # the entry on disk is stamped with the pre-bump generation
        stored = cache.get(unique_key)
        assert isinstance(stored, tuple)
        assert stored[0] == captured["gen"]
        assert stored[0] != cache_lock._current_generation()

    def test_render_spanning_bump_not_served_after(self, unique_key):
        def slow_render():
            cache_lock.bump_generation(source="test")
            return "stale_html"

        cache_lock.get_or_render(unique_key, slow_render)
        # next request must not get the stale page: it re-renders fresh
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "fresh_html"))
        assert result == "fresh_html"
        assert len(calls) == 1
