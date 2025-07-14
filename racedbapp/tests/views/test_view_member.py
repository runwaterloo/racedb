import datetime

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_member_endpoint_success(create_rwmember):
    client = APIClient()
    rwmember = create_rwmember()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_member_endpoint_fivek_pb(create_result, create_rwmember):
    client = APIClient()
    rwmember = create_rwmember()
    result = create_result(rwmember=rwmember)
    result.guntime = datetime.timedelta(seconds=600)  # 10 minutes, definitely PB for 5 or 10 km
    result.save()
    # test 5 km PB
    result.event.distance.slug = "5-km"
    result.event.distance.save()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200
    # test 10 km PB
    result.event.distance.slug = "10-km"
    result.event.distance.save()
    url = f"/member/{rwmember.slug}/"
    response = client.get(url)
    assert response.status_code == 200
