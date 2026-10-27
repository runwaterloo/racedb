import pytest
from rest_framework.test import APIClient

from racedbapp.models import Config, Rwmembertag
from racedbapp.view_boost import get_gender_finishers, get_previous_races


def make_boost_tag_2025():
    return Rwmembertag.objects.create(name="boost-2025")


def make_boost_config():
    for name, value in (
        ("boost_max_events", "5"),
        ("boost_max_endurrun", "5"),
        ("boost_max_sport", "5"),
        ("boost_leaderboard_size", "10"),
        ("boost_merit_max", "10"),
        ("boost_participation_points", "1"),
        ("boost_pb_points", "1"),
        ("boost_classic_points", "1"),
        ("boost_ditto_points", "1"),
        ("nophoto_url", ""),
    ):
        Config.objects.create(name=name, value=value)


@pytest.mark.django_db
def test_boost_endpoint_success():
    client = APIClient()
    url = "/boost/2025/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_boost_endpoint_with_results(create_f_m_results, create_rwmember, create_result):
    data = create_f_m_results
    make_boost_config()
    rwmember = create_rwmember()
    rwmember.joindate = data["event"].date
    rwmember.gender = "M"
    rwmember.year_of_birth = 1990
    rwmember.tags.add(make_boost_tag_2025())
    rwmember.save()
    result = create_result(event=data["event"], rwmember=rwmember, gender="M", place=3, name_suffix="m3")
    result.gender_place = 2
    result.save()
    client = APIClient()
    response = client.get("/boost/2025/")
    assert response.status_code == 200
    # member-specific view also renders
    response = client.get(f"/boost/2025/?member={rwmember.slug}")
    assert response.status_code == 200


@pytest.mark.django_db
def test_boost_endpoint_member_not_found(create_f_m_results):
    create_f_m_results
    make_boost_tag_2025()
    client = APIClient()
    response = client.get("/boost/2025/?member=no-such-member")
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_gender_finishers_counts_f_m_per_event(create_f_m_results, create_result):
    data = create_f_m_results
    # extra results in a second event, plus excluded rows
    event2 = create_result(name_suffix="e2", gender="M", place=1).event
    create_result(event=event2, gender="F", place=2, name_suffix="e2f")
    # excluded: non-binary gender and place >= 990000
    create_result(event=data["event"], gender="NB", place=4, name_suffix="nb")
    create_result(event=data["event"], gender="M", place=990000, name_suffix="huge")
    gender_finishers = get_gender_finishers(data["event"].date, data["event"].date)
    assert gender_finishers["F"][data["event"].id] == 1
    assert gender_finishers["M"][data["event"].id] == 1
    assert gender_finishers["F"][event2.id] == 1
    assert gender_finishers["M"][event2.id] == 1
    assert "NB" not in gender_finishers


@pytest.mark.django_db
def test_get_gender_finishers_excludes_place_990000(create_f_m_results, create_result):
    data = create_f_m_results
    create_result(event=data["event"], gender="M", place=990000, name_suffix="huge")
    gender_finishers = get_gender_finishers(data["event"].date, data["event"].date)
    assert gender_finishers["M"][data["event"].id] == 1


@pytest.mark.django_db
def test_get_previous_races_groups_by_member_and_race(
    create_rwmember, create_event, create_result
):
    member = create_rwmember()
    race = create_event().race
    event_prev_1 = create_event(race=race, date="2024-03-01", name_suffix="p1")
    event_prev_2 = create_event(race=race, date="2024-06-01", name_suffix="p2")
    event_current = create_event(date="2025-03-01", name_suffix="cur")  # different race
    create_result(event=event_prev_1, rwmember=member, name_suffix="m1")
    create_result(event=event_prev_2, rwmember=member, name_suffix="m2")
    create_result(event=event_current, rwmember=member, name_suffix="mc")
    other = create_rwmember(name_suffix="other")
    create_result(event=event_prev_1, rwmember=other, name_suffix="o1", place=2)
    included_members = [member.id, other.id]
    previous_races = get_previous_races(2025, included_members)
    assert previous_races[member.id] == {event_prev_1.race_id, event_prev_2.race_id}
    assert previous_races[other.id] == {event_prev_1.race_id}
    # current-year event must not appear
    assert event_current.race_id not in previous_races[member.id]


@pytest.mark.django_db
def test_get_previous_races_empty_for_no_results(create_rwmember):
    member = create_rwmember()
    previous_races = get_previous_races(2025, [member.id])
    assert previous_races == {}
