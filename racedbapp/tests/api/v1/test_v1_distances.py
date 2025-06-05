import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from racedbapp.models import Distance


@pytest.fixture
def distances_test_setup(db):
    Distance.objects.create(name="5K", km=5, slug="5k")
    username = "apitestuser"
    password = "testpass123"
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    client.login(username=username, password=password)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    return client, headers


def test_distances_list_returns_results(distances_test_setup):
    client, headers = distances_test_setup
    response = client.get("/v1/distances/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list), "Expected a list of results"
    assert len(data["results"]) > 0, "Expected at least one result in the response"


def test_distances_list_fields(distances_test_setup):
    client, headers = distances_test_setup
    response = client.get("/v1/distances/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "next" in data
    assert "previous" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    result = data["results"][0]
    expected_fields = {
        "id",
        "slug",
        "name",
        "km",
        "showrecord",
    }
    assert set(result.keys()) == expected_fields
