import pytest
from rest_framework.test import APIClient


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
