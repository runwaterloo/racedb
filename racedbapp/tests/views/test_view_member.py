import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from racedbapp import view_member
from racedbapp.models import Category, Result, Samerace


@pytest.mark.django_db
def test_member_endpoint_success(create_rwmember):
    client = APIClient()
    rwmember = create_rwmember()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_member_endpoint_fivek_pb(create_result, create_rwmember):
    client = APIClient()
    rwmember = create_rwmember()
    result = create_result(rwmember=rwmember)
    result.guntime = datetime.timedelta(seconds=600)  # 10 minutes, definitely PB for 5 or 10 km
    result.save()
    # test 5 km PB
    result.event.distance.slug = "5-km"
    result.event.distance.save()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200
    # test 10 km PB
    result.event.distance.slug = "10-km"
    result.event.distance.save()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200


def test_race_win_badge_remaps_old_race_and_avoids_repeat_queries(
    create_event, create_race, create_rwmember
):
    """A win at a race that has a Samerace mapping should credit the current
    race, and the lookup must happen once, not per win."""
    old_race = create_race(name_suffix="old")
    current_race = create_race(name_suffix="current")
    Samerace.objects.create(old_race=old_race, current_race=current_race)
    member = create_rwmember()
    event1 = create_event(name_suffix="w1", race=old_race)
    event2 = create_event(name_suffix="w2", race=old_race)
    category = Category.objects.create(name="40-49")
    for event in (event1, event2):
        Result.objects.create(
            event=event,
            category=category,
            athlete=f"A {member.slug}",
            gender="M",
            city="X",
            place=1,
            gender_place=1,
            guntime=datetime.timedelta(minutes=20),
            rwmember=member,
        )
    view_member.get_race_win_badges.cache_clear() if hasattr(
        view_member.get_race_win_badges, "cache_clear"
    ) else None
    with CaptureQueriesContext(connection) as ctx:
        badges = view_member.get_race_win_badges(
            [
                type("NR", (), {"result": r, "gender_place": 1})
                for r in Result.objects.filter(rwmember=member)
            ]
        )
    assert len(badges) == 1
    assert badges[0].name == f"Won an overall event at {current_race.name}"
    samerace_queries = [q for q in ctx.captured_queries if "samerace" in q["sql"]]
    assert len(samerace_queries) <= 1


@pytest.mark.django_db
def test_inaugural_badge_batches_race_queries(create_event, create_race, create_rwmember):
    """Inaugural badges: first-year finish flagged, later years not, and the
    per-race first-year lookup must be one aggregate query, not one per race."""
    race = create_race(name_suffix="inaug")
    member = create_rwmember()
    category = Category.objects.create(name="Open")
    first_event = create_event(name_suffix="first", date="2010-01-01", race=race)
    later_event = create_event(name_suffix="later", date="2020-01-01", race=race)
    other_race = create_race(name_suffix="other")
    other_event = create_event(name_suffix="other", date="2015-01-01", race=other_race)
    for event in (first_event, later_event, other_event):
        Result.objects.create(
            event=event,
            category=category,
            athlete=f"A {member.slug}",
            gender="F",
            city="X",
            place=1,
            gender_place=1,
            guntime=datetime.timedelta(minutes=20),
            rwmember=member,
        )
    results = [
        type("NR", (), {"result": r, "gender_place": 1})
        for r in Result.objects.filter(rwmember=member).order_by("-event__date")
    ]
    with CaptureQueriesContext(connection) as ctx:
        badges = view_member.get_inaugural_finishes_badges(results)
    names = [b.name for b in badges]
    assert names == [
        "Finished inaugural Test Race inaug",
        "Finished inaugural Test Race other",
    ]
    event_min_queries = [
        q for q in ctx.captured_queries if "MIN(" in q["sql"].upper() and "event" in q["sql"]
    ]
    assert len(event_min_queries) <= 1


@pytest.mark.django_db
def test_member_null_place_columns(create_result, create_rwmember, db):
    """Regression for prod 500 (2026-11-11): a result row with NULL
    gender_place/category_place (empty gender or empty category) must not
    crash sorting and must render blank, like the old computed sentinel ""."""
    member = create_rwmember()
    # empty gender -> gender_place stays NULL (prod import behavior)
    create_result(rwmember=member, gender="", place=115, name_suffix="nullplace")
    # empty category name -> category_place stays NULL (prod import behavior)
    empty_category = Category.objects.create(name="")
    create_result(rwmember=member, category=empty_category, place=60, name_suffix="nullcat")
    create_result(rwmember=member, gender="M", place=50, name_suffix="placed")
    from rest_framework.test import APIClient

    response = APIClient().get(f"/member/{member.slug}/")
    assert response.status_code == 200
    assert b"None" not in response.content
