import pytest
from django.core.management import call_command

from racedbapp.models import Config, Event
from racedbapp.view_index import get_featured_event


@pytest.mark.django_db
def test_homepage_featured_event_fixture_loads():
    call_command("flush", interactive=False)
    call_command("loaddata", "race", "distance", "sequel", "event", "series", "config")

    config = Config.objects.get(name="homepage_featured_event_id")
    assert config.value == "24"

    featured_event = Event.objects.get(pk=24)
    assert featured_event.race_id == 2
    assert featured_event.distance_id == 2
    assert featured_event.date.isoformat() == "2026-10-18"
    assert get_featured_event() == featured_event
