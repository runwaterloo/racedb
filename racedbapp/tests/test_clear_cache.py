from unittest.mock import patch

import pytest

from racedbapp import tasks


@pytest.fixture(autouse=True)
def clear_django_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_clear_cache_runs_purge():
    """clear_cache ends with a stale-entry purge (issue #430)."""
    from racedbapp.shared import cache_lock

    with (
        patch.object(cache_lock, "bump_generation") as mock_bump,
        patch.object(tasks, "purge_stale_cache") as mock_purge,
    ):
        tasks.clear_cache(source="test")
    mock_bump.assert_called_once_with(source="test")
    mock_purge.assert_called_once()


def test_clear_cache_does_not_enqueue_warm_cache():
    """clear_cache bumps the generation only; no warming task exists."""
    from django.core.cache import cache

    with patch.object(tasks, "safe_enqueue") as mock_enqueue:
        tasks.clear_cache(source="test")
    assert cache.get("index.") is None
    mock_enqueue.assert_not_called()


def test_clear_cache_requires_source():
    # clear_cache feeds the generation-bump log line; a source is mandatory
    with pytest.raises(TypeError):
        tasks.clear_cache()


class FakeRedis:
    """Minimal redis stand-in: scan_iter over a fixed key list."""

    def __init__(self, keys):
        self.keys = keys

    def scan_iter(self):
        yield from self.keys


@pytest.mark.django_db
def test_purge_deletes_stale_keeps_current():
    """Entries stamped below the current generation are deleted; current ones survive."""
    from django.core.cache import cache

    from racedbapp.shared import cache_lock

    cache.set("stale.key", (1, "old"), 3600)
    cache_lock.bump_generation(source="test")  # stale.key is now orphaned
    cache.set("fresh.key", (cache_lock._current_generation(), "new"), 3600)
    fake = FakeRedis([cache.make_key("stale.key"), cache.make_key("fresh.key")])
    with patch.object(cache_lock, "_redis_connection", return_value=fake):
        cache_lock.purge_stale_cache()
    assert cache.get("stale.key") is None
    assert cache.get("fresh.key") == (cache_lock._current_generation(), "new")


@pytest.mark.django_db
def test_purge_skips_non_stamped_keys():
    """Generation counter, lock keys and watcher state survive the purge."""
    from django.core.cache import cache

    from racedbapp.shared import cache_lock

    cache_lock.bump_generation(source="test")
    cache.set("cache_watcher.fingerprint", "abc", 3600)
    cache.set("cache_watcher.last_run", 123.0, 3600)
    cache.set("singleflight.index.", "lock-token", 120)
    keys = [
        cache.make_key("cache_generation"),
        cache.make_key("singleflight.index."),
        cache.make_key("cache_watcher.fingerprint"),
    ]
    fake = FakeRedis(keys)
    with patch.object(cache_lock, "_redis_connection", return_value=fake):
        cache_lock.purge_stale_cache()
    assert cache.get("cache_generation") is not None
    assert cache.get("singleflight.index.") is not None
    assert cache.get("cache_watcher.fingerprint") is not None


@pytest.mark.django_db
def test_purge_skips_on_non_redis_backend():
    """Without redis (locmem in tests), purge logs and does nothing."""
    from racedbapp.shared import cache_lock

    assert cache_lock._redis_connection() is None
    cache_lock.purge_stale_cache()  # should not raise
