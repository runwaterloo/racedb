import pytest
from rest_framework.test import APIClient

from racedbapp.models import Result
from racedbapp.view_series import set_ismaster_from_result


@pytest.mark.django_db
def test_series_endpoint_missing():
    client = APIClient()
    url = "/series/does-not-exist/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_series_endpoint_success(create_series):
    client = APIClient()
    series = create_series()
    url = f"/series/{series.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_series_endpoint_with_filter(create_series):
    client = APIClient()
    series = create_series()
    first_result = Result.objects.first()
    first_result.age = 40
    first_result.save()
    for filter in (
        "Female",
        "Male",
        "Masters",
        "F-Masters",
        "M-Masters",
        "some-category",
    ):
        url = f"/series/{series.slug}/?filter={filter}"
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_set_ismaster_from_result(create_result):
    result = create_result()
    scenarios = [
        {"age": None, "category_ismasters": False, "expected_result": False},
        {"age": None, "category_ismasters": True, "expected_result": True},
        {"age": 39, "category_ismasters": False, "expected_result": False},
        {"age": 39, "category_ismasters": True, "expected_result": False},
        {"age": 40, "category_ismasters": False, "expected_result": True},
        {"age": 40, "category_ismasters": True, "expected_result": True},
    ]
    for scenario in scenarios:
        result.age = scenario["age"]
        result.category.ismasters = scenario["category_ismasters"]
        result.save()
        assert set_ismaster_from_result(result) is scenario["expected_result"]
