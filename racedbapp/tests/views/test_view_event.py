import types

import pytest
from rest_framework.test import APIClient

from racedbapp.models import Result
from racedbapp.shared.types import Filter
from racedbapp.view_event import annotate_isrwfirst, get_category_filter


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
def test_event_endpoint_sequel(create_event, create_sequel):
    client = APIClient()
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/{event.sequel.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_multiple_with_sequel(create_distance, create_event, create_race, create_sequel):
    client = APIClient()
    distance = create_distance()
    race = create_race()
    sequel = create_sequel()
    event1 = create_event(distance=distance, race=race)
    create_event(distance=distance, race=race, sequel=sequel)
    url = f"/event/{event1.date.year}/{event1.race.slug}/{event1.distance.slug}/"
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


# below here is AI generated and a bit complicated, but it works
@pytest.fixture
def mock_event():
    return types.SimpleNamespace(
        date=types.SimpleNamespace(year=2024),
        race=types.SimpleNamespace(slug="test-race"),
        distance=types.SimpleNamespace(slug="test-distance"),
        sequel=None,
    )


def get_choice_names(f):
    return [c.name for c in f.choices]


@pytest.mark.parametrize(
    "category,division,expected_current,expected_choices,not_expected_choices,all_url_contains",
    [
        ("All", "All", "All (2)", ["Female", "Masters", "Cat1", "Cat2"], [], None),
        ("Cat1", "All", "Cat1 (1)", ["All", "Female", "Masters", "Cat2"], ["Cat1"], None),
        ("Cat1", "A", "Cat1 (1)", ["All"], ["Cat1"], "?division=A"),
        ("All", "A", None, [], [], "division=A"),
    ],
)
def test_get_category_filter_parametrized(
    monkeypatch,
    mock_event,
    category,
    division,
    expected_current,
    expected_choices,
    not_expected_choices,
    all_url_contains,
):
    # Patch Result.objects.filter to return a mock queryset with count()
    class MockQueryset(list):
        def count(self):
            return len(self)

        def filter(self, *args, **kwargs):
            return self

    # Simulate results for the mock event
    mock_results = MockQueryset([object(), object()])  # 2 results for 'All'
    monkeypatch.setattr(
        "racedbapp.view_event.Result.objects.filter", lambda *args, **kwargs: mock_results
    )

    # Patch helper functions to return predictable categories
    monkeypatch.setattr(
        "racedbapp.view_event.get_genders",
        lambda event, division: [
            {"category__name": "Female", "count": 1},
        ],
    )
    monkeypatch.setattr(
        "racedbapp.view_event.get_masters",
        lambda event, division: [
            {"category__name": "Masters", "count": 1},
        ],
    )
    monkeypatch.setattr(
        "racedbapp.view_event.get_categories",
        lambda event, division: [
            {"category__name": "Cat1", "count": 1},
            {"category__name": "Cat2", "count": 1},
        ],
    )

    f = get_category_filter(mock_event, category=category, division=division)
    assert isinstance(f, Filter)
    if expected_current:
        assert f.current == expected_current
    names = get_choice_names(f)
    for expected in expected_choices:
        assert any(expected in n for n in names)
    for not_expected in not_expected_choices:
        assert not any(n.startswith(not_expected) for n in names)
    if all_url_contains:
        # For Cat1/A, the first choice is All with ?division=A; for All/A, all choices have division=A
        if category != "All":
            assert f.choices[0].name.startswith("All")
            assert all_url_contains in f.choices[0].url
        else:
            for c in f.choices:
                assert "division=A" in c.url or "filter=" in c.url
