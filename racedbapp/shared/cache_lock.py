"""
Simple cache helper for expensive views.

get_or_render(key, render_func) returns the cached value for key, or
renders it, stores it, and returns it. There is deliberately no locking:
if two requests miss at the same time they both render, and the last one
to write wins. That is acceptable because cold renders are fast (the
queries behind these views have been optimized) and duplicate renders
are harmless.

Invalidation: call clear(source), which empties the whole cache. Every
invalidation path in the repo funnels through tasks.clear_cache, which
calls this and then enqueues a warm pass — so there is a single path to
clearing and every clear is attributable in the logs.

All cache reads/writes of page content go through get() / set() (or
get_or_render()) in this module so the TTL policy stays in one place.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Safety TTL: bounds staleness if an invalidation path is ever missed.
ENTRY_TTL_SECONDS = 30 * 3600  # 30h


def get_or_render(cache_key, render_func):
    """Return the cached value for cache_key, rendering and storing on miss."""
    cached = get(cache_key)
    if cached is not None:
        return cached
    value = render_func()
    set(cache_key, value)
    return value


def get(cache_key):
    """Read a cache entry; missing means None."""
    return cache.get(cache_key)


def set(cache_key, value):
    """Store a cache entry with the standard safety TTL."""
    cache.set(cache_key, value, ENTRY_TTL_SECONDS)


def clear(source):
    """Clear the entire cache.

    source is required (a short string like "watcher", "addraces",
    "clearcache-view", "config_save") so every clear in the logs is
    attributable. There are no mystery callers: invalidation paths in
    this repo all pass one.
    """
    if not source or not isinstance(source, str):
        raise ValueError("clear requires a source string")
    cache.clear()
    logger.info("cache clear: source=%s", source)
