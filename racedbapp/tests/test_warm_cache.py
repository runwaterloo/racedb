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
        tasks.clear_cache()
    assert cache.get("index.") is None
    mock_enqueue.assert_called_once_with(tasks.warm_cache)
