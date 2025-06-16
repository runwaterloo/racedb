import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_boost_endpoint_success():
    client = APIClient()
    url = "/boost/2025/"
    response = client.get(url)
    assert response.status_code == 200
