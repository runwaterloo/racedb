import datetime

import pytest
from rest_framework.test import APIClient

from racedbapp import view_member
from racedbapp.models import Result


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
