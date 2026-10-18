"""
Single-flight locking for expensive cached views.

Problem this solves: when a cache key is missing and many requests for it
arrive at once, every request renders the page from scratch (seconds of CPU
each). With the lock, the first request renders and the rest wait for the
result to appear in the cache, so N concurrent requests cost one render.

The lock is stored in the Django cache (cache.add is atomic across backends,
including redis and locmem). Design notes:

- The lock has a TTL so a crashed renderer cannot deadlock the key forever.
- Waiters poll the cache for the rendered page. If the lock disappears
  without the page appearing (crashed renderer, TTL expiry), a waiter takes
  the lock and renders. If a waiter waits longer than WAIT_TIMEOUT_SECONDS,
  it renders anyway, which degrades to the previous behaviour rather than
  hanging forever.
"""

import time
import uuid

from django.core.cache import cache

LOCK_TTL_SECONDS = 120  # auto-release if a renderer dies; > WAIT_TIMEOUT_SECONDS
WAIT_TIMEOUT_SECONDS = 60  # how long waiters wait before rendering themselves
POLL_INTERVAL_SECONDS = 0.1


def get_or_render(cache_key, render_func):
    """Return the cached value for cache_key, rendering at most once."""
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    lock_key = _lock_key(cache_key)
    lock_token = str(uuid.uuid4())
    if cache.add(lock_key, lock_token, LOCK_TTL_SECONDS):
        return _render_under_lock(cache_key, lock_key, lock_token, render_func)
    return _wait_for_cache_or_render(cache_key, lock_key, render_func)


def _lock_key(cache_key):
    return "singleflight.{}".format(cache_key)


def _render_under_lock(cache_key, lock_key, lock_token, render_func):
    try:
        value = render_func()
    except Exception:
        _release_lock(lock_key, lock_token)
        raise
    cache.set(cache_key, value)
    _release_lock(lock_key, lock_token)
    return value


def _wait_for_cache_or_render(cache_key, lock_key, render_func):
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        if cache.get(lock_key) is None:
            lock_token = str(uuid.uuid4())
            if cache.add(lock_key, lock_token, LOCK_TTL_SECONDS):
                return _render_under_lock(cache_key, lock_key, lock_token, render_func)
    return render_func()


def _release_lock(lock_key, lock_token):
    # Only delete the lock if it is still ours: the lock may have expired and
    # been taken over by another request while we were rendering.
    if cache.get(lock_key) == lock_token:
        cache.delete(lock_key)
