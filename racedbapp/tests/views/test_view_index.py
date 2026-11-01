import datetime
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import Client
from rest_framework.test import APIClient

from racedbapp import view_index
from racedbapp.models import Config, Series
from racedbapp.shared import cache_lock


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
def test_featured_event_without_previous_event_uses_unlinked_year_heading(create_event):
    event = create_event(date=datetime.date.today() + datetime.timedelta(days=30))
    Config.objects.bulk_create([Config(name="homepage_featured_event_id", value=str(event.id))])
    client = Client(raise_request_exception=False)

    response = client.get(f"/?asofdate={event.date.isoformat()}")

    assert response.status_code == 200
    content = response.content.decode()
    assert f"<th>{event.date.year - 1} Winner</th>" in content


@pytest.mark.django_db
@pytest.mark.parametrize("with_sequel", [False, True])
def test_event_winner_headings_use_most_recent_previous_event(
    create_event, create_sequel, monkeypatch, with_sequel
):
    older_event = create_event(date=datetime.date(2020, 1, 1))
    previous_event = create_event(
        date=datetime.date(2022, 1, 1),
        race=older_event.race,
        distance=older_event.distance,
        sequel=create_sequel() if with_sequel else None,
    )
    upcoming_event = create_event(
        date=datetime.date(2030, 1, 1), race=older_event.race, distance=older_event.distance
    )
    record = SimpleNamespace(
        place="Female",
        athlete="Record Holder",
        member=None,
        guntime=datetime.timedelta(minutes=19),
        year=2019,
    )
    previous_winner = SimpleNamespace(
        female_athlete="Previous Winner",
        female_member_slug=None,
        female_time=datetime.timedelta(minutes=20),
    )
    monkeypatch.setattr(view_index, "get_recap_results_standard", lambda event: [previous_winner])
    monkeypatch.setattr(view_index, "get_event_records", lambda race, distance: [record])

    event_data = view_index.get_event_data(upcoming_event)

    content = render_to_string(
        "racedbapp/index.html",
        {
            "featured_event": upcoming_event,
            "featured_event_data": event_data,
            "future_events": [(upcoming_event, event_data, "test-race")],
        },
    )

    upcoming_section = content.split("<strong>UPCOMING EVENTS</strong>", 1)[1].split(
        "All Future Events", 1
    )[0]
    sequel_path = f"{previous_event.sequel.slug}/" if previous_event.sequel else ""
    expected_event_link = (
        f'href="/event/{previous_event.date.year}/{previous_event.race.slug}/'
        f'{previous_event.distance.slug}/{sequel_path}">{previous_event.date.year}</a> Winner'
    )
    assert expected_event_link in upcoming_section


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


@pytest.mark.django_db
def test_get_future_events_includes_all_events_of_chosen_races(create_event, monkeypatch):
    """All no-result events of the first N races show, not just the first per race."""
    race_a_event1 = create_event(name_suffix="a1", date=datetime.date(2030, 6, 1))
    race_a = race_a_event1.race
    event_a2 = create_event(
        name_suffix="a2", date=datetime.date(2030, 7, 1), race=race_a
    )
    event_b = create_event(name_suffix="b", date=datetime.date(2030, 8, 1))
    monkeypatch.setattr(view_index, "get_event_data", lambda event: False)

    future_events = view_index.get_future_events(event=None)

    event_ids = [i.id for i, _, _ in future_events]
    assert race_a_event1.id in event_ids
    assert event_a2.id in event_ids
    assert event_b.id in event_ids
    assert len(event_ids) == 3


@pytest.mark.django_db
def test_get_future_events_skips_events_with_results_without_consuming_race_slot(
    create_event, create_category, create_result, monkeypatch
):
    """An event with results is hidden and its race can still be chosen later."""
    race_a = create_event(name_suffix="a1", date=datetime.date(2030, 6, 1)).race
    done_event = create_event(
        name_suffix="a2", date=datetime.date(2030, 7, 1), race=race_a
    )
    category = create_category()
    create_result(event=done_event, category=category)
    upcoming_event = create_event(
        name_suffix="a3", date=datetime.date(2030, 9, 1), race=race_a
    )
    monkeypatch.setattr(view_index, "get_event_data", lambda event: False)

    future_events = view_index.get_future_events(event=None)

    event_ids = [i.id for i, _, _ in future_events]
    assert done_event.id not in event_ids
    assert upcoming_event.id in event_ids


@pytest.mark.django_db
def test_get_future_events_excluded_events_do_not_consume_race_slot(
    create_event, monkeypatch
):
    """Excluded events neither show nor mark their race as seen."""
    excluded = create_event(name_suffix="ex", date=datetime.date(2030, 6, 1))
    other = create_event(name_suffix="b", date=datetime.date(2030, 7, 1))
    Config.objects.bulk_create(
        [
            Config(name="homepage_upcoming_exclude_events", value=str(excluded.id)),
            Config(name="homepage_upcoming_races_count", value="1"),
        ]
    )
    monkeypatch.setattr(view_index, "get_event_data", lambda event: False)

    future_events = view_index.get_future_events(event=None)

    event_ids = [i.id for i, _, _ in future_events]
    assert excluded.id not in event_ids
    assert other.id in event_ids


@pytest.mark.django_db
def test_get_event_records_matches_get_race_records(
    create_event, create_result, create_race, create_distance, create_category
):
    """get_event_records must match the subset of get_race_records the
    index table consumes: same demographics, athletes, times, years."""
    race = create_race()
    distance = create_distance()
    e1 = create_event(race=race, distance=distance, date=datetime.date(2024, 1, 1))
    e2 = create_event(race=race, distance=distance, date=datetime.date(2025, 1, 1))
    category = create_category()
    create_result(event=e1, gender="M", guntime=datetime.timedelta(minutes=17), age=45, category=category, athlete="Fast Master", place=1)
    create_result(event=e2, gender="M", guntime=datetime.timedelta(minutes=17), age=20, category=category, athlete="Fast Open", place=1)
    create_result(event=e2, gender="M", guntime=datetime.timedelta(minutes=18), age=50, category=category, place=2)
    create_result(event=e1, gender="F", guntime=datetime.timedelta(minutes=19), age=42, category=category, place=2)
    create_result(event=e2, gender="F", guntime=datetime.timedelta(minutes=20), age=20, category=category, place=3)

    new = view_index.get_event_records(race, distance)
    old = view_index.shared.get_race_records(race, distance, individual_only=True)

    def key(r):
        return (r.place, r.athlete, r.guntime, r.year)

    assert sorted(map(key, new)) == sorted(map(key, old))
    # tie between master and open male at 17:00 means 2 rows for males
    males = [r for r in new if r.place in ("Overall Male", "Masters Male")]
    assert {r.athlete for r in males} == {"Fast Master", "Fast Open"}


@pytest.mark.django_db
def test_junk_query_params_share_warm_cache_with_bare_index(create_event):
    """
    Only asofdate affects the rendered page. Junk params (e.g. ?author=1)
    must not create distinct cache keys - they hit the same "index" key.
    """
    cache_lock.set("index", HttpResponse("<html>warm</html>"))
    client = Client(raise_request_exception=False)
    response = client.get("/?author=1")
    assert response.status_code == 200
    assert response.content.decode() == "<html>warm</html>"


@pytest.mark.django_db
def test_asofdate_bypasses_cache(create_category, create_event, create_result):
    """
    asofdate requests short-circuit to an uncached render: a poisoned cache
    entry must not leak into the asofdate response, and the response must
    not be stored under any index cache key.
    """
    event = create_event()
    category = create_category(name_suffix="a")
    create_result(event=event, gender="F", category=category, place=1)
    create_result(event=event, gender="F", category=category, place=3)
    create_result(event=event, gender="F", category=category, place=5)
    create_result(event=event, gender="M", category=category, place=2)
    create_result(event=event, gender="M", category=category, place=4)
    create_result(event=event, gender="M", category=category, place=6)
    cache_lock.set("index", HttpResponse("<html>stale</html>"))
    client = Client(raise_request_exception=False)

    response = client.get("/?asofdate=2025-01-01")

    assert response.status_code == 200
    assert "stale" not in response.content.decode()

    # The asofdate render must not have overwritten the cache entry.
    assert cache_lock.get("index").content.decode() == "<html>stale</html>"
