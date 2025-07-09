import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_recap_endpoint_no_results(create_event):
    client = APIClient()
    event = create_event()
    url = f"/recap/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200


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
