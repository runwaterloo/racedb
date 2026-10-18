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
    """With no cache_warm_urls Config, warm "/" via the Django test client."""
    client = MagicMock(spec=Client)
    client.get.return_value.status_code = 200
    with (
        patch.object(tasks, "WEBHOST", "http://localhost"),
        patch("racedbapp.tasks.Client", return_value=client),
    ):
        tasks.warm_cache()
    client.get.assert_called_once_with("/")


@pytest.mark.django_db
def test_warm_cache_config_urls():
    """cache_warm_urls Config entries (comma-separated) are each warmed."""
    from racedbapp.models import Config

    Config.objects.create(name="cache_warm_urls", value="/,/boost/2026/")
    client = MagicMock(spec=Client)
    with (
        patch.object(tasks, "WEBHOST", "http://localhost"),
        patch("racedbapp.tasks.Client", return_value=client),
    ):
        tasks.warm_cache()
    assert client.get.call_args_list[0][0] == ("/",)
    assert client.get.call_args_list[1][0] == ("/boost/2026/",)


def test_clear_cache_enqueues_warm_cache():
    """clear_cache schedules warm_cache right after clearing."""
    from django.core.cache import cache

    with patch.object(tasks, "safe_enqueue") as mock_enqueue:
        tasks.clear_cache()
    assert cache.get("index.") is None
    mock_enqueue.assert_called_once_with(tasks.warm_cache)
