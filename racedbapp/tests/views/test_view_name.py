import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_name_noindex():
    client = APIClient()
    response = client.get("/name/?q=smith")
    assert response.status_code == 200
    assert b'<meta name="robots" content="noindex">' in response.content
