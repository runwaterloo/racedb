import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_endurrace_no_results():
    client = APIClient()
    url = "/endurrace/2025/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_enudrrace_endpoint_year(create_distance, create_race, create_event, create_result):
    client = APIClient()
    distance = create_distance()
    distance.slug = "8-km"
    distance.save()
    race = create_race()
    race.slug = "endurrace"
    race.save()
    event = create_event(distance=distance, race=race, date="2025-01-01")
    create_result(event=event)
    # should get a 200 response with results for the year 2025
    url = "/endurrace/2025/"
    response = client.get(url)
    assert response.status_code == 200
    # should get a 200 response with results for the year latest
    url = "/endurrace/latest/"
    response = client.get(url)
    assert response.status_code == 200
    # should get a 404 response with results for the year 2026
    url = "/endurrace/2026/"
    response = client.get(url)
    assert response.status_code == 404
