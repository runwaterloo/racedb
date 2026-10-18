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
        cache.set(unique_key, "cached_html")
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls))
        assert result == "cached_html"
        assert calls == []

    def test_renders_and_caches_when_missing(self, unique_key):
        calls = []
        result = cache_lock.get_or_render(unique_key, make_render_func(calls, "html1"))
        assert result == "html1"
        assert cache.get(unique_key) == "html1"
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
        cache.set(unique_key, "warm_html")
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
    assert response2.content == response1.content
    assert len(render_count) == 1
