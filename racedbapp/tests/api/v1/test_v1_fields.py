# This test ensures that each API endpoint returns exactly the fields specified in endpoints.json.
# It helps catch accidental changes to API response structure and enforces contract consistency.

import json
import os

import pytest

from racedbapp.api.v1.serializers import V1DistanceSerializer
from racedbapp.models import Distance

# Load endpoint definitions from JSON file
with open(os.path.join(os.path.dirname(__file__), "endpoints.json")) as f:
    ENDPOINTS = [e for e in json.load(f) if "fields" in e]  # Only endpoints with non-empty fields


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_api_list_and_fields(authenticated_client, request, endpoint):
    factory = request.getfixturevalue(endpoint["factory"])
    factory()
    client, headers = authenticated_client
    response = client.get(endpoint["url"], **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    result = data["results"][0]
    assert set(result.keys()) == set(endpoint["fields"])


def test_distance_serializer_results_url_no_request(db):
    distance = Distance.objects.create(
        name="Test Distance", km=5, slug="test-distance", showrecord=False
    )
    serializer = V1DistanceSerializer(distance, context={})
    data = serializer.data
    # When no request is in context, should return relative url
    assert data["results_url"] == f"/v1/distances/{distance.id}/results/"
