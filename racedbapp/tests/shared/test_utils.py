from unittest.mock import patch

from racedbapp.shared.utils import get_achievement_image, get_race_logo_slug


def test_get_achievement_image_file_exists():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=True):
        result = get_achievement_image("slug", "badge")
        assert result == "badge-slug.png"


def test_get_achievement_image_file_missing():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        result = get_achievement_image("slug", "badge")
        assert result == "generic_100x100.png"


def test_get_race_logo_slug_file_exists():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=True):
        assert get_race_logo_slug("baden-road-races") == "baden-road-races"


def test_get_race_logo_slug_file_missing():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        assert get_race_logo_slug("does-not-exist") == "rw-race-logo"


def test_get_race_logo_slug_non_string_slug():
    assert get_race_logo_slug(None) == "rw-race-logo"
    assert get_race_logo_slug(401) == "rw-race-logo"
