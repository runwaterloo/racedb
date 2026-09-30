from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from racedbapp import process_photoupdate


@pytest.mark.django_db
def test_get_event_photos_searches_main_event_tag(
    create_event, create_race, create_distance, monkeypatch
):
    race = create_race()
    race.slug = "sport"
    race.save()
    distance = create_distance()
    distance.slug = "10-km"
    distance.save()
    event = create_event(date="2026-01-01", race=race, distance=distance)
    search = Mock(return_value={"photos": {"pages": 1, "photo": []}})
    monkeypatch.setattr(
        process_photoupdate,
        "flickr",
        SimpleNamespace(photos=SimpleNamespace(search=search)),
    )

    assert process_photoupdate.get_event_photos(event) == []

    search.assert_called_once()
    assert search.call_args.kwargs["tags"] == "2026sport10-km"
    assert search.call_args.kwargs["tag_mode"] == "all"


@pytest.mark.django_db
def test_get_event_photos_searches_sequel_event_tag(
    create_event, create_race, create_distance, create_sequel, monkeypatch
):
    race = create_race()
    race.slug = "sport"
    race.save()
    distance = create_distance()
    distance.slug = "10-km"
    distance.save()
    sequel = create_sequel(slug="stage-4-doubleheader")
    event = create_event(
        date="2026-01-01", race=race, distance=distance, sequel=sequel
    )
    search = Mock(return_value={"photos": {"pages": 1, "photo": []}})
    monkeypatch.setattr(
        process_photoupdate,
        "flickr",
        SimpleNamespace(photos=SimpleNamespace(search=search)),
    )

    assert process_photoupdate.get_event_photos(event) == []

    search.assert_called_once()
    assert search.call_args.kwargs["tags"] == "2026sport10-kmstage-4-doubleheader"
    assert search.call_args.kwargs["tag_mode"] == "all"
