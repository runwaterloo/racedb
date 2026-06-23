from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from racedbapp.templatetags.racedbapp_extras import event_logo, round_up


def test_round_up_no_microseconds():
    t = timedelta(seconds=10)
    assert round_up(t) == t


def test_round_up_with_microseconds():
    t = timedelta(seconds=10, microseconds=123456)
    expected = timedelta(seconds=11)
    assert round_up(t) == expected


@pytest.mark.parametrize(
    "input_td,expected_td",
    [
        (timedelta(seconds=0, microseconds=1), timedelta(seconds=1)),
        (timedelta(seconds=5, microseconds=999999), timedelta(seconds=6)),
        (timedelta(seconds=42, microseconds=0), timedelta(seconds=42)),
    ],
)
def test_round_up_various(input_td, expected_td):
    assert round_up(input_td) == expected_td


def test_round_up_none():
    assert round_up(None) is None


@pytest.mark.django_db
def test_event_logo_uses_race_slug_when_file_exists(create_event):
    event = create_event()
    with patch("racedbapp.shared.utils.Path.is_file", return_value=True):
        assert event_logo(event) == "/static/race_logos/test-race-a.png"


@pytest.mark.django_db
def test_event_logo_falls_back_when_file_missing(create_event):
    event = create_event()
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        assert event_logo(event) == "/static/race_logos/rw-race-logo.png"


@pytest.mark.django_db
def test_event_logo_prefers_custom_logo_url(create_event):
    event = create_event()
    event.custom_logo_url = "http://example.com/logo.png"
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        assert event_logo(event) == "http://example.com/logo.png"


def test_event_logo_uses_race_slug_for_relay_view_model():
    # The relay view passes a flattened EventV with `race_slug` and no `.race`.
    event = SimpleNamespace(race_slug="test-race-a")
    with patch("racedbapp.shared.utils.Path.is_file", return_value=True):
        assert event_logo(event) == "/static/race_logos/test-race-a.png"


def test_event_logo_relay_view_model_falls_back_when_file_missing():
    event = SimpleNamespace(race_slug="does-not-exist")
    with patch("racedbapp.shared.utils.Path.is_file", return_value=False):
        assert event_logo(event) == "/static/race_logos/rw-race-logo.png"


def test_event_logo_falls_back_when_no_race_info():
    # Neither a `.race` relation nor a `race_slug` attribute is present.
    event = SimpleNamespace()
    assert event_logo(event) == "/static/race_logos/rw-race-logo.png"
