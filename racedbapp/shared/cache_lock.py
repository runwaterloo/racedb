"""
Single-flight locking for expensive cached views, with generation-based
invalidation.

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

Generation-based invalidation:

- Content is stored as (generation, value). A single global counter is kept
  in the cache under GENERATION_KEY. A cached entry is a hit only if its
  generation matches the current one; stale-generation entries are treated
  exactly like misses and expire naturally (ENTRY_TTL_SECONDS).
- Invalidating the cache means calling bump_generation(). It does NOT delete
  entries, so a render that started before the bump stores an old generation
  and is ignored on read — cache.clear() while renders are in flight was the
  way stale pages could be re-cached and live forever.
- A safety TTL (ENTRY_TTL_SECONDS) bounds staleness if invalidation stops
  happening (e.g. a broken watcher): entries expire after 30 hours.

CONTRACT: all cache reads/writes of page content go through get() / set()
(or get_or_render()) in this module. Direct cache.get/cache.set of content
elsewhere is not allowed — such entries will not be generation-stamped and
will never be treated as hits. Only the generation counter and the
single-flight lock keys live outside this scheme, and both are private to
this module.
"""

import time
import uuid

from django.core.cache import cache

LOCK_TTL_SECONDS = 120  # auto-release if a renderer dies; > WAIT_TIMEOUT_SECONDS
WAIT_TIMEOUT_SECONDS = 60  # how long waiters wait before rendering themselves
POLL_INTERVAL_SECONDS = 0.1
GENERATION_KEY = "cache_generation"
GENERATION_TTL_SECONDS = None  # the counter must never expire
ENTRY_TTL_SECONDS = 30 * 3600  # 30h safety TTL on cached content


def get_or_render(cache_key, render_func):
    """Return the cached value for cache_key, rendering at most once."""
    cached = get(cache_key)
    if cached is not None:
        return cached
    lock_key = _lock_key(cache_key)
    lock_token = str(uuid.uuid4())
    if cache.add(lock_key, lock_token, LOCK_TTL_SECONDS):
        return _render_under_lock(cache_key, lock_key, lock_token, render_func)
    return _wait_for_cache_or_render(cache_key, lock_key, render_func)


def get(cache_key):
    """Read a generation-stamped cache entry; stale/missing means None."""
    cached = cache.get(cache_key)
    if not _entry_is_current(cached):
        return None
    return cached[1]


def set(cache_key, value):
    """Store a cache entry stamped with the current generation."""
    generation = _current_generation()
    cache.set(cache_key, (generation, value), ENTRY_TTL_SECONDS)


def bump_generation():
    """Invalidate all generation-stamped cache entries.

    Does not delete anything: old entries become unreadable (stale
    generation) and expire on their own TTL.
    """
    # cache.add only succeeds if the key does not exist yet, so this is
    # atomic: create at 2 (initial generation is 1), otherwise increment.
    if not cache.add(GENERATION_KEY, 2, GENERATION_TTL_SECONDS):
        cache.incr(GENERATION_KEY)


def _entry_is_current(cached):
    if not isinstance(cached, tuple) or len(cached) != 2:
        return False
    return cached[0] == _current_generation()


def _current_generation():
    generation = cache.get(GENERATION_KEY)
    if generation is None:
        return 1
    return generation


def _lock_key(cache_key):
    return "singleflight.{}".format(cache_key)


def _render_under_lock(cache_key, lock_key, lock_token, render_func):
    try:
        value = render_func()
    except Exception:
        _release_lock(lock_key, lock_token)
        raise
    set(cache_key, value)
    _release_lock(lock_key, lock_token)
    return value


def _wait_for_cache_or_render(cache_key, lock_key, render_func):
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        cached = get(cache_key)
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
