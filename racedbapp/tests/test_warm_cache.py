from unittest.mock import MagicMock, patch

import pytest
from django.test import Client

from racedbapp import tasks


@pytest.fixture(autouse=True)
def clear_django_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_warm_cache_default_single_url():
    """Warm "/" via the Django test client."""
    client = MagicMock(spec=Client)
    client.get.return_value.status_code = 200
    with (
        patch.object(tasks, "WEBHOST", "http://localhost"),
        patch("racedbapp.tasks.Client", return_value=client),
    ):
        tasks.warm_cache()
    client.get.assert_called_once_with("/")


@pytest.mark.django_db
def test_warm_cache_hardcoded_urls():
    """Every URL in WARM_URLS is warmed via the Django test client."""
    client = MagicMock(spec=Client)
    client.get.return_value.status_code = 200
    with (
        patch.object(tasks, "WEBHOST", "http://localhost"),
        patch("racedbapp.tasks.Client", return_value=client),
    ):
        tasks.warm_cache()
    warmed = [call[0][0] for call in client.get.call_args_list]
    assert warmed == tasks.WARM_URLS


def test_clear_cache_enqueues_warm_cache():
    """clear_cache schedules warm_cache right after clearing."""
    from django.core.cache import cache

    with patch.object(tasks, "safe_enqueue") as mock_enqueue:
        tasks.clear_cache(source="test")
    assert cache.get("index.") is None
    mock_enqueue.assert_called_once_with(tasks.warm_cache)


@pytest.mark.django_db
def test_warm_cache_adds_scheme_to_bare_host():
    """A WEBHOST without a scheme gets https:// prefixed in warm_cache."""
    with (
        patch.object(tasks, "WEBHOST", "results.runwaterloo.com"),
        patch(
            "racedbapp.tasks.requests.get", return_value=MagicMock(status_code=200)
        ) as mocked_get,
    ):
        tasks.warm_cache()
    mocked_get.assert_called_once()
    mocked_get.assert_called_once()
    url = mocked_get.call_args[0][0]
    assert url == "https://results.runwaterloo.com/"


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


@pytest.mark.django_db
def test_warm_cache_runs_purge():
    """warm_cache ends with a stale-entry purge (issue #430)."""

    client = MagicMock(spec=Client)
    client.get.return_value.status_code = 200
    with (
        patch.object(tasks, "WEBHOST", "http://localhost"),
        patch("racedbapp.tasks.Client", return_value=client),
        patch("racedbapp.tasks.purge_stale_cache") as mock_purge,
    ):
        tasks.warm_cache()
    mock_purge.assert_called_once()
