import pytest
from rest_framework.test import APIClient

from racedbapp.models import Result
from racedbapp.view_event import annotate_isrwfirst


@pytest.mark.django_db
def test_event_endpoint_success(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.django_db
def test_event_endpoint_missing():
    client = APIClient()
    url = "/event/2025/fake-race/fake-event/"
    response = client.get(url)
    assert response.status_code == 404


def test_event_endpoint_sequel(create_event, create_sequel):
    client = APIClient()
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/{event.sequel.slug}/"
    response = client.get(url)
    assert response.status_code == 200


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


@pytest.mark.django_db
def test_event_isrwfirst(create_category, create_event, create_result, create_rwmember):
    """
    Test that annotate_isrwfirst correctly annotates:
    - True for a member's first event (as a member)
    - False for subsequent events
    - False for results with no rwmember
    """
    event1 = create_event(date="2025-01-01", name_suffix="1")
    event2 = create_event(date="2025-02-01", name_suffix="2")
    event3 = create_event(date="2025-03-01", name_suffix="3")
    category = create_category()
    rwmember = create_rwmember(joindate="2025-01-02")
    create_result(event=event1, category=category, place=1, rwmember=rwmember)
    create_result(event=event1, category=category, place=2, rwmember=None)
    create_result(event=event2, category=category, place=1, rwmember=rwmember)
    create_result(event=event3, category=category, place=1, rwmember=rwmember)

    ## check event1 ##
    results = Result.objects.filter(event=event1)
    annotated_results = annotate_isrwfirst(results)
    # check that first result has isrwfirst attribue
    assert hasattr(annotated_results[0], "isrwfirst")
    # check that first result (member) has isrwfirst set to False (it's before joindate)
    assert annotated_results[0].isrwfirst is False
    # check that second result (non-member) has isrwfirst set to False
    assert annotated_results[1].isrwfirst is False

    ## check event2 ##
    results = Result.objects.filter(event=event2)
    annotated_results = annotate_isrwfirst(results)
    # check that first result (member) has isrwfirst set to True (it's after joindate)
    assert annotated_results[0].isrwfirst is True

    ## check event3 ##
    results = Result.objects.filter(event=event3)
    annotated_results = annotate_isrwfirst(results)
    # check that first result (member) has isrwfirst set to False (the 1st was event2)
    assert annotated_results[0].isrwfirst is False
