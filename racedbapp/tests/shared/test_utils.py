from unittest.mock import patch

from racedbapp.shared.utils import get_achievement_image


def test_get_achievement_image_file_exists():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=True):
        result = get_achievement_image("slug", "badge")
        assert result == "badge-slug.png"


def test_get_achievement_image_file_missing():
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        result = get_achievement_image("slug", "badge")
        assert result == "generic_100x100.png"
