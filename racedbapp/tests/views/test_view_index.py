import pytest
from rest_framework.test import APIClient

from racedbapp.models import Series


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
def test_view_recap_includes_series_dropdown(create_series):
    series = create_series()
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert "<select" in content
    assert '<option value="#">Series</option>' in content
    assert (
        f'<option value="/series/{series.slug}/?year={series.year}">{series.name}</option>'
    ) in content


@pytest.mark.django_db
def test_view_recap_series_dropdown_shows_name_only(create_series):
    series = create_series()
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert (
        f'<option value="/series/{series.slug}/?year={series.year}">{series.name}</option>'
    ) in content


@pytest.mark.django_db
def test_view_recap_includes_series_for_any_listed_event(create_series):
    series = create_series()
    series.event_ids = series.event_ids.split(",", 1)[0]
    series.save()
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert (
        f'<option value="/series/{series.slug}/?year={series.year}">{series.name}</option>'
    ) in content


@pytest.mark.django_db
def test_view_recap_includes_multiple_series_in_dropdown(create_series):
    first_series = create_series()
    second_series = Series.objects.create(
        year=2026,
        name="Another Series",
        slug="another-series",
        event_ids=first_series.event_ids,
    )
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert content.count('<option value="/series/') == 2
    assert (
        f'<option value="/series/{first_series.slug}/?year={first_series.year}">'
        f"{first_series.name}</option>"
    ) in content
    assert (
        f'<option value="/series/{second_series.slug}/?year={second_series.year}">'
        f"{second_series.name}</option>"
    ) in content


@pytest.mark.django_db
def test_view_recap_excludes_series_link_for_event_without_series(create_event, create_result):
    event = create_event()
    create_result(event=event)
    client = APIClient()

    response = client.get("/?asofdate=2025-01-01")
    content = response.content.decode()

    assert "<select" not in content
    assert '<option value="#">Series</option>' not in content
