import datetime

import pytest
from rest_framework.test import APIClient

from racedbapp.models import Endurathlete, Result


@pytest.mark.django_db
def test_race_endpoint_success(create_f_m_results):
    client = APIClient()
    race_slug = create_f_m_results["race"].slug
    distance_slug = create_f_m_results["distance"].slug
    url = f"/race/{race_slug}/{distance_slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_race_endpoint_race_not_found(create_distance):
    client = APIClient()
    distance = create_distance()
    url = f"/race/fake-race/{distance.slug}/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_race_endpoint_distance_not_found(create_race):
    client = APIClient()
    race = create_race()
    url = f"/race/{race.slug}/fake-distance/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_race_endpoint_ultimate_division(
    create_distance, create_race, create_category, create_event, create_result
):
    """Ultimate division renders only athletes who finished all events.

    Covers the prefetched-athlete path in _get_race_records: results
    whose athlete has no Endurathlete row, or who did not finish the
    year's last endurrun event, are excluded from the page.
    """
    client = APIClient()
    race = create_race(name_suffix="x")
    race.slug = "endurrun"
    race.save()
    # view_race reorders endurrun distances by hardcoded 7-stage layout,
    # so the fixture needs all 7 to exist.
    distances = [create_distance(name_suffix=f"s{i}") for i in range(7)]
    for d in distances:
        create_event(race=race, distance=d, date="2025-07-01", name_suffix="stage")
    distance = distances[0]
    event1 = create_event(race=race, distance=distance, date="2025-07-01", name_suffix="e1")
    event2 = create_event(race=race, distance=distance, date="2025-07-08", name_suffix="e2")
    category = create_category(name_suffix="x")
    results = [
        # (event, athlete, gender, place) -- division set below.
        (event1, "Alice A", "F", 1),
        (event2, "Alice A", "F", 1),
        (event1, "Bob B", "M", 2),
        (event2, "Bob B", "M", 2),
        (event1, "Carl C", "M", 3),
        (event2, "Carl C", "M", 990001),
        (event1, "Zoe Z", "F", 4),
    ]
    for event, athlete, gender, place in results:
        Result.objects.create(
            event=event,
            category=category,
            athlete=athlete,
            gender=gender,
            place=place,
            division="Ultimate",
            guntime=datetime.timedelta(seconds=300),
        )
    Endurathlete.objects.create(
        year=2025, division="Ultimate", name="Alice A", gender="F", city="c", province="p", country="CA"
    )
    Endurathlete.objects.create(
        year=2025, division="Ultimate", name="Bob B", gender="M", city="c", province="p", country="CA"
    )
    Endurathlete.objects.create(
        year=2025, division="Ultimate", name="Carl C", gender="M", city="c", province="p", country="CA"
    )
    url = f"/race/endurrun/{distance.slug}/?division=Ultimate"
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    # The main results list shows all division results (DNFs included,
    # pre-existing behavior). The record tables must only show athletes
    # with an Endurathlete row who finished the year's last event.
    # Records section runs from <h4>Records</h4> to the Top 50 heading.
    records_start = content.find("<h4>Records</h4>")
    records_end = content.find("<h4>Top 50</h4>")
    records_html = content[records_start:records_end]
    assert "Alice A" in content  # finisher: in results and records
    assert "Bob B" in content  # finisher: in results and records
    assert "Carl C" in content  # DNF: main results only
    assert "Carl C" not in records_html
    assert "Zoe Z" not in records_html  # no Endurathlete row
