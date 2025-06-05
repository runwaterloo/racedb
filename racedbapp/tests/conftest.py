import datetime

import pytest

from racedbapp.models import Category, Distance, Event, Race, Result


@pytest.fixture
def create_f_m_results(db):
    distance = Distance.objects.create(name="Test Distance", km=99, slug="test-distance")
    race = Race.objects.create(name="Test Race", slug="test-race")
    category = Category.objects.create(name="Test Category")
    event = Event.objects.create(
        race=race, distance=distance, date=datetime.date(2025, 1, 1), city="Test City"
    )
    result_f = Result.objects.create(
        event=event,
        category=category,
        athlete="Test Athlete F",
        gender="F",
        city="Test City",
        place=1,
    )
    result_m = Result.objects.create(
        event=event,
        category=category,
        athlete="Test Athlete M",
        gender="M",
        city="Test City",
        place=2,
    )
    return {
        "distance": distance,
        "race": race,
        "category": category,
        "event": event,
        "result_m": result_m,
        "result_f": result_f,
    }
