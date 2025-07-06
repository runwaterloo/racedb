import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_success():
    client = APIClient()
    url = "/health/"
    response = client.get(url)
    assert response.status_code == 200
