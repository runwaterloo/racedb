import pytest
from rest_framework.test import APIClient


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
