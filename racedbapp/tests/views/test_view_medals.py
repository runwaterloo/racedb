import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_medals_endpoint_success(create_event):
    client = APIClient()
    event = create_event()
    url = f"/medals/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    response = client.get(url)
    assert response.status_code == 200
