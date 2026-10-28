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


@pytest.mark.django_db
def test_place_counts_match_old_semantics(create_event, create_category, create_rwmember):
    """Window-function counts must equal per-row COUNT(place__lte=...) for
    every member result, including places >= 990000."""
    m = create_rwmember()
    other = create_rwmember(name_suffix="b")
    event = create_event(name_suffix="eq")
    cat_f = create_category("f40")
    cat_m = create_category("m40")
    rows = [
        (m, "F", 1, cat_f),
        (other, "F", 2, cat_f),
        (other, "F", 3, cat_f),
        (m, "M", 4, cat_m),
        (other, "M", 5, cat_m),
        (other, "M", 990000, cat_m),  # DNF-style place
    ]
    for rwmember, gender, place, category in rows:
        Result.objects.create(
            event=event,
            category=category,
            athlete=f"A {rwmember.slug} {place}",
            gender=gender,
            city="X",
            place=place,
            guntime=None,
            rwmember=rwmember,
        )
    event2 = create_event(name_suffix="eq2")
    Result.objects.create(
        event=event2,
        category=cat_f,
        athlete="A",
        gender="F",
        city="X",
        place=2,
        guntime=None,
        rwmember=m,
    )
    dbresults = list(
        Result.objects.select_related()
        .filter(rwmember=m)
        .exclude(place__gte=990000)
        .order_by("-event__date", "-event__distance__km")
    )
    gender_counts, category_counts = view_member.get_place_counts(dbresults)
    for r in dbresults:
        old_gp = Result.objects.filter(
            event=r.event, gender=r.gender, place__lte=r.place
        ).count()
        assert gender_counts[(r.event_id, r.gender, r.place)] == old_gp, f"gp {r.id}"
        if r.category.name != "":
            old_cp = Result.objects.filter(
                event=r.event, category=r.category, place__lte=r.place
            ).count()
            assert category_counts[(r.event_id, r.category_id, r.place)] == old_cp, f"cp {r.id}"


@pytest.mark.django_db
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
