from datetime import timedelta

import pytest

from racedbapp.templatetags.racedbapp_extras import round_up


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
