import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_event_endpoint_success(create_event):
    client = APIClient()
    event = create_event()
    url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200
