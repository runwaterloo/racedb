import datetime

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from racedbapp.models import Category, Distance, Event, Race, Result, Rwmember, Series


@pytest.fixture
def test_user(db):
    username = "apitestuser"
    password = "testpass123"
    user = User.objects.create_user(username=username, password=password)
    return user, username, password


@pytest.fixture
def authenticated_client(db, test_user):
    _user, username, password = test_user
    client = APIClient()
    client.login(username=username, password=password)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    return client, headers


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
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
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
        rwmember=None,
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
            guntime=datetime.timedelta(seconds=300),
            rwmember=rwmember,
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
    result_f.gender_place = 1
    result_f.save()
    result_m.gender_place = 1
    result_m.save()
    return {
        "distance": distance,
        "race": race,
        "category_f": category_f,
        "category_m": category_m,
        "event": event,
        "result_m": result_m,
        "result_f": result_f,
    }


@pytest.fixture
def create_series(db, create_distance, create_race, create_category, create_event, create_result):
    def _create_series(**kwargs):
        race = create_race()
        distance1 = create_distance(name_suffix="first", km=5)
        distance2 = create_distance(name_suffix="second", km=10)
        event1 = create_event(race=race, distance=distance1, name_suffix="first")
        event2 = create_event(race=race, distance=distance2, name_suffix="second")
        category = create_category()
        create_result(event=event1, category=category)
        create_result(event=event2, category=category)
        series_defaults = dict(
            year=2025,
            name="Test Series",
            slug="test-series",
            event_ids=f"{event1.id},{event2.id}",
        )
        series_defaults.update(kwargs)
        return Series.objects.create(**series_defaults)

    return _create_series


@pytest.fixture
def create_rwmember(db):
    def _create_rwmember(name_suffix="a", joindate=datetime.date(2025, 1, 1), active=True):
        if isinstance(joindate, str):
            joindate = datetime.date.fromisoformat(joindate)
        return Rwmember.objects.create(
            name=f"RW Member {name_suffix}",
            slug=f"rw-member-{name_suffix.lower()}",
            city=f"City {name_suffix}",
            joindate=joindate,
            active=active,
        )

    return _create_rwmember


@pytest.fixture
def create_tag(db):
    def _create_tag(name="TestTag", auto_select=True):
        from racedbapp.models import Rwmembertag

        return Rwmembertag.objects.create(name=name, auto_select=auto_select)

    return _create_tag


@pytest.fixture
def create_prime(db, create_event):
    def _create_prime(event=None):
        from racedbapp.models import Prime

        if not event:
            event = create_event()
        return Prime.objects.create(event=event, place=1, gender="F")

    return _create_prime
