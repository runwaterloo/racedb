import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from racedbapp.models import Category, Distance, Event, Race, Result


@pytest.fixture
def results_test_setup(db):
    race = Race.objects.create(name="Test Race")
    distance = Distance.objects.create(name="5K", km=5, slug="5k")
    event = Event.objects.create(
        race_id=race.id, distance_id=distance.id, date="2025-01-01", city="TestCity"
    )
    category = Category.objects.create(name="TestCat")
    Result.objects.create(
        event=event,
        category=category,
        athlete="Test Athlete",
        gender="M",
        city="TestCity",
        place=1,
    )
    username = "apitestuser"
    password = "testpass123"
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    client.login(username=username, password=password)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    return client, headers


def test_results_list_returns_results(results_test_setup):
    client, headers = results_test_setup
    response = client.get("/v1/results/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list), "Expected a list of results"
    assert len(data["results"]) > 0, "Expected at least one result in the response"


def test_results_list_fields(results_test_setup):
    client, headers = results_test_setup
    response = client.get("/v1/results/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "next" in data
    assert "previous" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    result = data["results"][0]
    expected_fields = {
        "id",
        "event",
        "place",
        "bib",
        "athlete",
        "rwmember",
        "gender",
        "gender_place",
        "category",
        "category_place",
        "age",
        "chiptime",
        "guntime",
        "city",
        "province",
        "country",
        "division",
        "isrwpb",
    }
    assert set(result.keys()) == expected_fields


def test_results_filter_by_event(results_test_setup):
    client, headers = results_test_setup
    # Create a second event and result
    race = Race.objects.create(name="Other Race", slug="other-race")
    distance = Distance.objects.create(name="10K", km=10, slug="10k")
    event2 = Event.objects.create(
        race_id=race.id, distance_id=distance.id, date="2025-01-02", city="OtherCity"
    )
    category = Category.objects.create(name="OtherCat")
    Result.objects.create(
        event=event2,
        category=category,
        athlete="Other Athlete",
        gender="F",
        city="OtherCity",
        place=2,
    )
    # Filter by the first event (should only return results for event_id=1)
    response = client.get("/v1/results/?event=1", **headers)
    data = response.json()
    assert all(result["event"] == 1 for result in data["results"])
    # Filter by the second event (should only return results for event_id=event2.id)
    response = client.get(f"/v1/results/?event={event2.id}", **headers)
    data = response.json()
    assert all(result["event"] == event2.id for result in data["results"])


def test_results_are_sorted_by_place_within_event(results_test_setup):
    client, headers = results_test_setup
    event = Result.objects.first().event
    category = Category.objects.get(name="TestCat")
    # Add multiple results with different places
    Result.objects.create(
        event=event, category=category, athlete="A", gender="M", city="TestCity", place=4
    )
    Result.objects.create(
        event=event, category=category, athlete="B", gender="M", city="TestCity", place=3
    )
    Result.objects.create(
        event=event, category=category, athlete="C", gender="M", city="TestCity", place=2
    )
    response = client.get("/v1/results/?event=1", **headers)
    data = response.json()
    places = [result["place"] for result in data["results"]]
    assert places == sorted(places), "Results are not sorted by place"
