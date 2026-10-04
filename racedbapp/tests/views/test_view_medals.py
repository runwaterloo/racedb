import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_medals_endpoint_success(create_event):
    client = APIClient()
    event = create_event()
    url = f"/medals/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_medals_endpoint_sequel(create_event, create_sequel, create_category, create_result):
    client = APIClient()
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    event.medals = "standard"
    event.save()
    create_result(
        event=event,
        category=create_category(name_suffix="open"),
        gender="F",
        place=1,
    )
    create_result(
        event=event,
        category=create_category(name_suffix="master", is_masters=True),
        gender="M",
        age=45,
        place=2,
    )

    url = (
        f"/medals/{event.date.year}/{event.race.slug}/"
        f"{event.distance.slug}/{event.sequel.slug}/"
    )
    response = client.get(url)
    assert response.status_code == 200
    event_url = (
        f"/event/{event.date.year}/{event.race.slug}/"
        f"{event.distance.slug}/{event.sequel.slug}/"
    )
    assert f'href="{event_url}"'.encode() in response.content
    assert sequel.name.encode() in response.content


@pytest.mark.django_db
def test_medals_endpoint_invalid_sequel(create_event, create_sequel, create_category, create_result):
    client = APIClient()
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    event.medals = "standard"
    event.save()
    create_result(
        event=event,
        category=create_category(name_suffix="open"),
        gender="F",
        place=1,
    )
    create_result(
        event=event,
        category=create_category(name_suffix="master", is_masters=True),
        gender="M",
        age=45,
        place=2,
    )

    url = (
        f"/medals/{event.date.year}/{event.race.slug}/"
        f"{event.distance.slug}/not-a-real-sequel/"
    )
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_medals_endpoint_sequel_event_not_on_bare_url(
    create_event, create_sequel, create_category, create_result
):
    client = APIClient()
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    event.medals = "standard"
    event.save()
    create_result(
        event=event,
        category=create_category(name_suffix="open"),
        gender="F",
        place=1,
    )
    create_result(
        event=event,
        category=create_category(name_suffix="master", is_masters=True),
        gender="M",
        age=45,
        place=2,
    )

    url = f"/medals/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 404
