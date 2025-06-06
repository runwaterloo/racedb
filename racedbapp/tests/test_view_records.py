from collections import namedtuple

import pytest
from rest_framework.test import APIClient


# Mocks for Django ORM objects and shared.get_race_records
class DummyRace:
    def __init__(self, id, name, shortname, slug):
        self.id = id
        self.name = name
        self.shortname = shortname
        self.slug = slug


class DummyDistance:
    def __init__(self, id, name, slug, km):
        self.id = id
        self.name = name
        self.slug = slug
        self.km = km


@pytest.mark.django_db
def test_records_endpoint_race_not_found(create_f_m_results):
    client = APIClient()
    distance_slug = create_f_m_results["distance"].slug
    url = f"/records/fake-race/{distance_slug}/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_records_endpoint_distance_not_found(create_f_m_results):
    client = APIClient()
    race_slug = create_f_m_results["race"].slug
    url = f"/records/{race_slug}/fake-distance/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_records_endpoint_success(create_f_m_results):
    client = APIClient()
    race_slug = create_f_m_results["race"].slug
    distance_slug = create_f_m_results["distance"].slug
    url = f"/records/{race_slug}/{distance_slug}/"
    response = client.get(url)
    assert response.status_code == 200


def test_resolve_race(monkeypatch):
    # Patch Race.objects.get
    def fake_get(slug):
        assert slug == "test-slug"
        return DummyRace(1, "Test Race", "TR", "test-slug")

    import racedbapp.view_records as vr

    monkeypatch.setattr(vr.Race.objects, "get", fake_get)
    race = vr.resolve_race("test-slug")
    assert race.id == 1
    assert race.name == "Test Race"
    assert race.shortname == "TR"
    assert race.slug == "test-slug"


def test_resolve_distance_combined():
    import racedbapp.view_records as vr

    dist = vr.resolve_distance("combined")
    assert dist.id == 0
    assert dist.name == "Combined"
    assert dist.slug == "combined"
    assert dist.km == 13


def test_resolve_distance(monkeypatch):
    def fake_get(slug):
        assert slug == "dist-slug"
        return DummyDistance(2, "5K", "dist-slug", 5)

    import racedbapp.view_records as vr

    monkeypatch.setattr(vr.Distance.objects, "get", fake_get)
    dist = vr.resolve_distance("dist-slug")
    assert dist.id == 2
    assert dist.name == "5K"
    assert dist.slug == "dist-slug"
    assert dist.km == 5


def test_build_context(monkeypatch):
    race = namedtuple("nr", ["id", "name", "shortname", "slug"])(1, "Race", "R", "slug")
    dist = namedtuple("nd", ["id", "name", "slug", "km"])(2, "5K", "dist", 5)

    def fake_get_race_records(race_arg, dist_arg):
        assert race_arg == race
        assert dist_arg == dist
        return ["rec"], ["team"], ["hill"]

    import racedbapp.view_records as vr

    monkeypatch.setattr(vr.shared, "get_race_records", fake_get_race_records)
    ctx = vr.build_context(race, dist)
    assert ctx["race"] == race
    assert ctx["distance"] == dist
    assert ctx["records"] == ["rec"]
    assert ctx["team_records"] == ["team"]
    assert ctx["hill_records"] == ["hill"]
    assert ctx["nomenu"] is True
