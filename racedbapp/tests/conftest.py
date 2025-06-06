import datetime

import pytest

from racedbapp.models import Category, Distance, Event, Race, Result


@pytest.fixture
def create_distance(db):
    def _create_distance(name_suffix="a", km=1):
        return Distance.objects.create(
            name=f"Test Distance {name_suffix}",
            km=km,
            slug=f"test-distance-{name_suffix.lower()}",
        )

    return _create_distance


@pytest.fixture
def create_race(db):
    def _create_race(name_suffix="a"):
        return Race.objects.create(
            name=f"Test Race {name_suffix}",
            slug=f"test-race-{name_suffix.lower()}",
        )

    return _create_race


@pytest.fixture
def create_event(db, create_race, create_distance):
    def _create_event(name_suffix="a", date=datetime.date(2025, 1, 1), race=None, distance=None):
        if race is None:
            race = create_race(name_suffix)
        if distance is None:
            distance = create_distance(name_suffix)
        return Event.objects.create(
            race=race,
            distance=distance,
            date=date,
            city=f"Test City {name_suffix}",
        )

    return _create_event


@pytest.fixture
def create_category(db):
    def _create_category(name_suffix="a"):
        return Category.objects.create(
            name=f"Test Category {name_suffix}",
        )

    return _create_category


@pytest.fixture
def create_result(db, create_event, create_category):
    def _create_result(
        event=None,
        category=None,
        name_suffix="a",
        gender="F",
        place=1,
    ):
        if event is None:
            event = create_event(name_suffix=name_suffix)
        if category is None:
            category = create_category(name_suffix)
        return Result.objects.create(
            event=event,
            category=category,
            athlete=f"Test Athlete {name_suffix}",
            gender=gender,
            city=f"Test City {name_suffix}",
            place=place,
        )

    return _create_result


@pytest.fixture
def create_f_m_results(
    db, create_distance, create_race, create_category, create_event, create_result
):
    distance = create_distance()
    race = create_race()
    event = create_event(race=race, distance=distance)
    category_f = create_category(name_suffix="f")
    category_m = create_category(name_suffix="m")
    result_f = create_result(event=event, category=category_f, name_suffix="f", gender="F", place=1)
    result_m = create_result(event=event, category=category_m, name_suffix="m", gender="M", place=2)
    return {
        "distance": distance,
        "race": race,
        "category_f": category_f,
        "category_m": category_m,
        "event": event,
        "result_m": result_m,
        "result_f": result_f,
    }
