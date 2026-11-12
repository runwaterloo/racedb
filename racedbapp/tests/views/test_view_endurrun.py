"""Tests for the endurrun view (ultimate / sport / relay).

The view is old, complicated and deliberately left unrefactored; these tests
exist as a behavioural safety net so refactoring and instrumentation work can
be verified against golden output.
"""

import datetime
import os

import pytest
from django.test import Client

import racedbapp
from racedbapp.models import Category, Distance, Endurathlete, Endurteam, Event, Race, Result


def make_client():
    return Client()


def make_endurrun_race():
    return Race.objects.create(name="Endurrun", slug="endurrun")


def make_category():
    category, _ = Category.objects.get_or_create(name="Open", ismasters=False)
    return category


def make_event(race, year, name_suffix="a"):
    distance, _ = Distance.objects.get_or_create(name="8 Km", slug="8-km", defaults={"km": 8})
    return Event.objects.create(
        race=race,
        distance=distance,
        date=datetime.date(year, 8, 20),
        city=f"Test City {name_suffix}",
    )


FLAGS_DIR = "/srv/racedb/racedbapp/static/flags"


@pytest.fixture
def flags(monkeypatch):
    """Stub only the view's hardcoded server path for flag images.

    A blanket os.listdir patch breaks the template engine's own directory
    scanning, so route only the flags path and delegate everything else.
    """
    real_listdir = os.listdir
    real_flags = os.path.join(os.path.join(os.path.dirname(racedbapp.__file__), "static", "flags"))

    def fake_listdir(path):
        if path == FLAGS_DIR:
            return real_listdir(real_flags)
        return real_listdir(path)

    monkeypatch.setattr("racedbapp.view_endurrun.os.listdir", fake_listdir)


def seed_ultimate(race, year=2025):
    """One event, two Ultimate athletes (F + M), each with one result."""
    event = make_event(race, year)
    Endurathlete.objects.create(
        year=year,
        division="Ultimate",
        name="Fiona Ultimate",
        gender="F",
        age=41,
        city="Waterloo",
        province="ON",
        country="Canada",
    )
    Endurathlete.objects.create(
        year=year,
        division="Ultimate",
        name="Marcus Ultimate",
        gender="M",
        age=30,
        city="Kitchener",
        province="ON",
        country="Canada",
    )
    Result.objects.create(
        event=event,
        category=make_category(),
        athlete="Fiona Ultimate",
        gender="F",
        place=1,
        division="Ultimate",
        guntime=datetime.timedelta(hours=5),
    )
    Result.objects.create(
        event=event,
        category=make_category(),
        athlete="Marcus Ultimate",
        gender="M",
        place=2,
        division="Ultimate",
        guntime=datetime.timedelta(hours=5, minutes=10),
    )
    return event


def seed_relay(race, year=2025):
    """One event, one relay team of two named legs with matching results.

    Note: the view derives the years list from Endurathlete (ultimate) rows
    even for the relay division, so a bare relay dataset 500s — we seed one
    Endurathlete to satisfy that.
    """
    Endurathlete.objects.create(
        year=year,
        division="Ultimate",
        name="Seed Athlete",
        gender="M",
        age=30,
        city="Waterloo",
        province="ON",
        country="Canada",
    )
    event = make_event(race, year, name_suffix="relay")
    Endurteam.objects.create(
        year=year,
        name="Test Team",
        gender="X",
        st1="Relay Leg One",
        st2="Relay Leg Two",
        st3="",
        st4="",
        st5="",
        st6="",
        st7="",
    )
    Result.objects.create(
        event=event,
        category=make_category(),
        athlete="Relay Leg One",
        gender="F",
        place=1,
        guntime=datetime.timedelta(hours=1),
    )
    Result.objects.create(
        event=event,
        category=make_category(),
        athlete="Relay Leg Two",
        gender="M",
        place=2,
        guntime=datetime.timedelta(hours=1, minutes=5),
    )


@pytest.mark.django_db
def test_ultimate_no_year(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2024)
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_year(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/?year=2025")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_year_filter_female(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/?year=2025&filter=Female")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_year_filter_phase(flags):
    """Phase cuts results at the given stage, showing leaders-so-far."""
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/?year=2025&filter=Female&phase=after-stage-1")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_contest_sprint(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/?contest=sprint&year=2025")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_dq_time(flags):
    """A guntime in the DQ window is marked DQ, not finished."""
    race = make_endurrun_race()
    event = make_event(race, 2025)
    Endurathlete.objects.create(
        year=2025,
        division="Ultimate",
        name="Disqualified Dan",
        gender="M",
        age=30,
        city="Waterloo",
        province="ON",
        country="Canada",
    )
    Result.objects.create(
        event=event,
        category=make_category(),
        athlete="Disqualified Dan",
        gender="M",
        place=1,
        division="Ultimate",
        guntime=datetime.timedelta(seconds=356400 + 30),  # 99:00:30 -> DQ window
    )
    response = make_client().get("/endurrun/ultimate/?year=2025")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_future_year_empty(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/ultimate/?year=2030")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ultimate_bad_year_404():
    make_endurrun_race()
    response = make_client().get("/endurrun/ultimate/?year=abcd")
    assert response.status_code == 404


@pytest.mark.django_db
def test_sport_year(flags):
    race = make_endurrun_race()
    seed_ultimate(race, 2025)
    response = make_client().get("/endurrun/sport/?year=2025")
    assert response.status_code == 200


@pytest.mark.django_db
def test_relay_year(flags):
    race = make_endurrun_race()
    seed_relay(race, 2025)
    response = make_client().get("/endurrun/relay/?year=2025")
    assert response.status_code == 200
