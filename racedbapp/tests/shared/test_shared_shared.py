import datetime

import pytest

from racedbapp.models import Category, Endurraceresult
from racedbapp.shared import shared


def test_set_distance_display_name(create_distance, create_sequel):
    # Create a distance and a sequel
    distance = create_distance()
    original_name = distance.name

    # Check display name is correct (no sequel)
    shared.set_distance_display_name(distance, None)
    assert distance.display_name == original_name

    # Check display name is correct (with sequel)
    sequel = create_sequel(name="Sequel Name")
    shared.set_distance_display_name(distance, sequel)
    assert distance.display_name == sequel.name






@pytest.mark.django_db
def test_get_race_records_combined(create_race, create_distance):
    """
    Regression test: the combined path uses Endurraceresult (no event FK),
    so get_race_records must not order its winners by event__date.
    https://results.runwaterloo.com/race/endurrace/combined/ 500ed since #458.
    """
    race = create_race()
    race.slug = "endurrace"
    race.save()
    distance = create_distance()
    distance.slug = "combined"
    distance.save()
    cat = Category.objects.first() or Category.objects.create(name="C")
    Endurraceresult.objects.create(
        year=2024,
        category=cat,
        athlete="Runner M",
        gender="M",
        city="W",
        guntime=datetime.timedelta(minutes=30),
        fivektime=datetime.timedelta(minutes=30),
        eightktime=datetime.timedelta(minutes=30),
    )
    Endurraceresult.objects.create(
        year=2024,
        category=cat,
        athlete="Runner F",
        gender="F",
        city="W",
        guntime=datetime.timedelta(minutes=35),
        fivektime=datetime.timedelta(minutes=35),
        eightktime=datetime.timedelta(minutes=35),
    )
    records, division_records, division_choices = shared.get_race_records(race, distance)
    assert records
    names = [r.athlete for r in records]
    assert "Runner M" in names
    assert "Runner F" in names
