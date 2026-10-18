"""
Instrumented cache backends.

These subclasses of the standard cache backends record cache operations as
Prometheus counters (exported via django-prometheus at /metrics):

- django_cache_get_total{view="index",result="hit"|"miss"}
- django_cache_op_total{view="index",operation="set"|"add"|"delete"|"clear"}

The `view` label is derived from the cache key prefix (the token before the
first dot, e.g. "index.0" -> "index"), keeping cardinality bounded to the
number of cached views rather than the number of cache keys.
"""

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.locmem import LocMemCache
from prometheus_client import Counter

django_cache_get = Counter(
    "django_cache_get",
    "Cache get operations, by cache key prefix and hit/miss",
    ["view", "result"],
)
django_cache_op = Counter(
    "django_cache_op",
    "Cache write/evict operations, by cache key prefix",
    ["view", "operation"],
)

_MISS = object()
_LABEL_MAX_LEN = 40


class InstrumentedCacheMixin:
    """Mixin adding Prometheus counters to any Django cache backend."""

    @staticmethod
    def _view_label(key):
        if key is None:
            return "none"
        prefix = str(key).split(".", 1)[0]
        return prefix[:_LABEL_MAX_LEN] or "none"

    def get(self, key, default=None, version=None):
        value = super().get(key, default=_MISS, version=version)
        if value is _MISS:
            django_cache_get.labels(view=self._view_label(key), result="miss").inc()
            return default
        django_cache_get.labels(view=self._view_label(key), result="hit").inc()
        return value

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        django_cache_op.labels(view=self._view_label(key), operation="set").inc()
        return super().set(key, value, timeout, version)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        django_cache_op.labels(view=self._view_label(key), operation="add").inc()
        return super().add(key, value, timeout, version)

    def delete(self, key, version=None):
        django_cache_op.labels(view=self._view_label(key), operation="delete").inc()
        return super().delete(key, version)

    def clear(self):
        django_cache_op.labels(view="all", operation="clear").inc()
        return super().clear()


class InstrumentedLocMemCache(InstrumentedCacheMixin, LocMemCache):
    """Instrumented locmem cache. Used mainly for tests."""


try:
    from django_redis.cache import RedisCache
except ImportError:  # pragma: no cover - django-redis is a hard dep in prod/dev
    pass
else:

    class InstrumentedRedisCache(InstrumentedCacheMixin, RedisCache):
        """Instrumented Redis cache (prod/dev default backend)."""
