import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_view_endpoint_success(create_category, create_event, create_result):
    """
    Currently the index view only works if at least one event exists,
    and has at least 3 female and 3 male results.
    """
    client = APIClient()
    event = create_event()
    category = create_category(name_suffix="a")
    create_result(event=event, gender="F", category=category, place=1)
    create_result(event=event, gender="F", category=category, place=3)
    create_result(event=event, gender="F", category=category, place=5)
    create_result(event=event, gender="M", category=category, place=2)
    create_result(event=event, gender="M", category=category, place=4)
    create_result(event=event, gender="M", category=category, place=6)
    url = "/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_view_recap_includes_series_link(create_series):
    series = create_series()
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert f'href="/series/{series.slug}/?year={series.year}"' in content
    assert series.name in content


@pytest.mark.django_db
def test_view_recap_excludes_series_link_for_event_without_series(create_event, create_result):
    event = create_event()
    create_result(event=event)
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert "?year=2025" not in content
