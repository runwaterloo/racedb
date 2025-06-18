import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_event_endpoint_success(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_endpoint_missing():
    client = APIClient()
    url = "/event/2025/fake-race/fake-event/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_endpoint_pages(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/?wheelchair=true"
    response = client.get(url)
    assert response.status_code == 200
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/?hill=true"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_endpoint_filter(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/?filter=somefilter"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_endpoint_division(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/?division=Ultimate"
    response = client.get(url)
    assert response.status_code == 200
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/?division=fakedivision"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_endpoint_hilldict(create_event, create_distance, create_race, create_prime):
    client = APIClient()
    distance = create_distance()
    distance.slug = "7-mi"
    distance.save()
    race = create_race()
    race.slug = "baden-road-races"
    race.save()
    event = create_event(distance=distance, race=race)
    create_prime(event=event)
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200
