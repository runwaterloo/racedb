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
