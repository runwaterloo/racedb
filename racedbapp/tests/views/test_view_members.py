import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_members_endpoint_success():
    client = APIClient()
    url = "/members/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_members_noindex_nofollow():
    client = APIClient()
    response = client.get("/members/")
    assert response.status_code == 200
    assert b'<meta name="robots" content="noindex, nofollow">' in response.content
