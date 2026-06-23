import datetime

import pytest
from rest_framework.test import APIClient

from racedbapp.models import Relay


@pytest.mark.django_db
def test_relay_index_renders(create_event, create_result):
    """End-to-end smoke test for the relay view.

    Regression guard for the relay 500: `event_logo` accessed
    `event.race.slug` on the relay view's flattened ``EventV`` (which has a
    ``race_slug`` but no ``.race``). See ``event_logo`` in
    ``racedbapp/templatetags/racedbapp_extras.py``.
    """
    event = create_event(name_suffix="relay")
    # Two individual finishers whose places the relay legs reference; the relay
    # view joins Relay.place back to these Result rows by "{year}-{place}".
    create_result(event=event, name_suffix="leg1", place=1)
    create_result(event=event, name_suffix="leg2", place=2)
    team_time = datetime.timedelta(minutes=10)
    for leg, place in ((1, 1), (2, 2)):
        Relay.objects.create(
            event=event,
            place=place,
            relay_team="Test Relay Team",
            relay_team_place=1,
            relay_team_time=team_time,
            relay_leg=leg,
        )

    client = APIClient()
    url = f"/relay/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)

    assert response.status_code == 200
    # The EventV has no matching logo file, so it falls back via event_logo.
    assert b"race_logos/rw-race-logo.png" in response.content
