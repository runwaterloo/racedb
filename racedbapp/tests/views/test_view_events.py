import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_events_endpoint_success_no_data():
    client = APIClient()
    url = "/events/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_endpoint_with_data(create_f_m_results):
    client = APIClient()
    url = "/events/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_endpoint_year():
    client = APIClient()
    url = "/events/?year=2025"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_endpoint_race(create_race):
    client = APIClient()
    url = "/events/?race=fake-race"
    response = client.get(url)
    assert response.status_code == 404
    race = create_race()
    url = f"/events/?race={race.slug}"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_endpoint_distance(create_distance):
    client = APIClient()
    url = "/events/?distance=fake-distance"
    response = client.get(url)
    assert response.status_code == 404
    distance = create_distance()
    url = f"/events/?distance={distance.slug}"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_endpoint_invalid_query_param(create_f_m_results):
    client = APIClient()
    response = client.get("/events/?bogus=1")
    assert response.status_code == 404


@pytest.mark.django_db
def test_events_endpoint_repeated_query_param(create_f_m_results):
    client = APIClient()
    response = client.get("/events/?year=2025&year=2026")
    assert response.status_code == 404


@pytest.mark.django_db
def test_events_cache_hit_and_bypass(create_f_m_results, monkeypatch):
    from django.core.cache import cache

    from racedbapp.shared import cache_lock

    cache.clear()
    client = APIClient()
    assert client.get("/events/").status_code == 200
    # Warm hit: rendering must not run again.
    calls = []

    def fail_render(cache_key, render_func):
        calls.append(cache_key)
        return render_func()

    monkeypatch.setattr(cache_lock, "get_or_render", fail_render)
    response = client.get("/events/")
    assert response.status_code == 200
    assert calls == []
    # cache=false cold-renders directly: never touches get_or_render, and
    # the cache entry stays warm for the next normal request.
    response = client.get("/events/?cache=false")
    assert response.status_code == 200
    assert calls == []
    response = client.get("/events/")
    assert response.status_code == 200
    assert calls == []


@pytest.mark.django_db
def test_events_cache_key_per_filter_shape(create_f_m_results):
    from django.http import HttpResponse

    from racedbapp.shared import cache_lock

    client = APIClient()
    shapes = ["", "?year=2025", "?race=test-race-a", "?distance=test-distance-a"]
    for qs in shapes:
        assert client.get(f"/events/{qs}").status_code == 200
    # Poison each key with a sentinel; a cache hit must return it verbatim.
    keys = [
        "events.all.all.all",
        "events.2025.all.all",
        "events.all.test-race-a.all",
        "events.all.all.test-distance-a",
    ]
    for key, qs in zip(keys, shapes):
        cache_lock.set(key, HttpResponse("sentinel"))
        response = client.get(f"/events/{qs}")
        assert response.status_code == 200
        assert response.content == b"sentinel"
