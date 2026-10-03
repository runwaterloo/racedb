import pytest
from django.test import Client
from rest_framework.test import APIClient

from racedbapp.models import Prime, Result


@pytest.fixture
def baden_road_recap_with_inactive_member(
    create_category, create_event, create_race, create_distance, create_result, create_rwmember
):
    race = create_race(name_suffix="inactive-recap")
    race.slug = "baden-road-races"
    race.save()
    distance = create_distance(name_suffix="inactive-recap")
    distance.slug = "7-mi"
    distance.save()
    event = create_event(
        name_suffix="inactive-recap",
        date="2025-01-01",
        race=race,
        distance=distance,
    )
    category = create_category(name_suffix="inactive-recap", is_masters=True)
    member = create_rwmember(name_suffix="inactive-recap", active=False)
    female_result = create_result(
        event=event, category=category, gender="F", place=1, rwmember=member
    )
    male_result = create_result(
        event=event, category=category, gender="M", place=2, rwmember=member
    )
    Prime.objects.create(event=event, place=female_result.place, gender="F")
    Prime.objects.create(event=event, place=male_result.place, gender="M")
    return event


@pytest.mark.django_db
def test_recap_endpoint_no_results(create_event):
    client = APIClient()
    event = create_event()
    url = f"/recap/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_recap_does_not_link_inactive_members(baden_road_recap_with_inactive_member):
    event = baden_road_recap_with_inactive_member
    response = Client().get(
        f"/recap/{event.date.year}/baden-road-races/7-mi/"
    )

    assert response.status_code == 200
    individual = response.context["individual_results"][0]
    hill = response.context["hill_results"][0]
    assert (
        individual.female_member_slug,
        individual.male_member_slug,
        hill.female_member_slug,
        hill.male_member_slug,
    ) == (None, None, None, None)


@pytest.mark.django_db
def test_topmasters_does_not_link_inactive_members(baden_road_recap_with_inactive_member):
    event = baden_road_recap_with_inactive_member

    topmasters = Result.objects.topmasters(event)

    assert (topmasters.female_member_slug, topmasters.male_member_slug) == (None, None)


@pytest.mark.django_db
def test_recap_endpoint_one_result(create_result):
    client = APIClient()
    result = create_result()
    url = f"/recap/{result.event.date.year}/{result.event.race.slug}/{result.event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_recap_endpoint_one_result_master_member(create_result, create_rwmember):
    client = APIClient()
    rwmember = create_rwmember()
    result = create_result(rwmember=rwmember)
    result.category.ismasters = True
    result.category.save()
    url = f"/recap/{result.event.date.year}/{result.event.race.slug}/{result.event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200
    # test male as well
    result.gender = "M"
    result.save()
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_recap_endpoint_six_results(create_category, create_event, create_result, create_rwmember):
    client = APIClient()
    event = create_event()
    category_f = create_category(name_suffix="f")
    rwmember_f = create_rwmember(name_suffix="f")
    category_m = create_category(name_suffix="m")
    rwmember_m = create_rwmember(name_suffix="m")
    result_1 = create_result(event=event, category=category_f, gender="F", place=1)
    result_2 = create_result(event=event, category=category_m, gender="M", place=2)
    result_1.rwmember = rwmember_f
    result_1.save()
    result_2.rwmember = rwmember_m
    result_2.save()
    create_result(event=event, category=category_f, gender="F", place=3)
    create_result(event=event, category=category_m, gender="M", place=4)
    create_result(event=event, category=category_f, gender="F", place=5)
    create_result(event=event, category=category_m, gender="M", place=6)
    url = f"/recap/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200
