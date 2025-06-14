from unittest.mock import patch

from django.core.management import call_command


def test_clear_cache_command():
    with patch("racedbapp.tasks.clear_cache") as mock_clear_cache:
        call_command("clear_cache")
        mock_clear_cache.assert_called_once()
