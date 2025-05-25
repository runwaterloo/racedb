import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_view_endpoint_success(create_category, create_event, create_result):
    """
    Currently the index view only works if at least one event exists,
    and has at least 3 female and 3 male results.
    """
    client = APIClient()
    event = create_event()
    category = create_category(name_suffix="a")
    create_result(event=event, gender="F", category=category, place=1)
    create_result(event=event, gender="F", category=category, place=3)
    create_result(event=event, gender="F", category=category, place=5)
    create_result(event=event, gender="M", category=category, place=2)
    create_result(event=event, gender="M", category=category, place=4)
    create_result(event=event, gender="M", category=category, place=6)
    url = "/"
    response = client.get(url)
    assert response.status_code == 200
