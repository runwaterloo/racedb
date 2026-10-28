import pytest
from django.test import Client

QA_HOST = "racedb.runwaterloo.com"
PROD_HOST = "results.runwaterloo.com"


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="tester", password="pw")


@pytest.mark.django_db
def test_qa_host_unauthenticated_gets_401(user):
    client = Client(HTTP_HOST=QA_HOST)
    response = client.get("/index/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_non_gated_host_unaffected(user):
    client = Client(HTTP_HOST=PROD_HOST)
    response = client.get("/index/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_default_testserver_host_unaffected(user):
    client = Client()
    response = client.get("/index/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_admin_login_allowed_unauthenticated(user):
    client = Client(HTTP_HOST=QA_HOST)
    response = client.get("/admin/login/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_gated(user):
    client = Client(HTTP_HOST=QA_HOST)
    response = client.get("/health/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_authenticated_user_gets_content(user):
    client = Client(HTTP_HOST=QA_HOST)
    client.login(username="tester", password="pw")
    response = client.get("/index/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_authenticated_user_on_prod_unaffected(user):
    client = Client(HTTP_HOST=PROD_HOST)
    client.login(username="tester", password="pw")
    response = client.get("/index/")
    assert response.status_code != 401
