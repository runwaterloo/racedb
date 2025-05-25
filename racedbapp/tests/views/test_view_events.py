import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_events_endpoint_success():
    client = APIClient()
    url = "/events/"
    response = client.get(url)
    assert response.status_code == 200
