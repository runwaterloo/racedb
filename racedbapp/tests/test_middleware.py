import pytest
from django.test import Client, override_settings

MIDDLEWARE_WITH_GATE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "racedbapp.middleware.QaAuthGateMiddleware",
]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="tester", password="pw")


@pytest.fixture
def gated_client():
    with override_settings(MIDDLEWARE=MIDDLEWARE_WITH_GATE):
        yield Client()


@pytest.mark.django_db
def test_unauthenticated_gets_401(gated_client, user):
    response = gated_client.get("/index/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_admin_root_allowed_redirects_to_login(gated_client, user):
    response = gated_client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_admin_no_slash_redirects(gated_client, user):
    # /admin (no slash) is redirected by the gate itself, before auth
    response = gated_client.get("/admin")
    assert response.status_code == 301
    assert response["Location"] == "/admin/"


@pytest.mark.django_db
def test_admin_login_allowed_unauthenticated(gated_client, user):
    response = gated_client.get("/admin/login/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_deep_path_gated(gated_client, user):
    response = gated_client.get("/admin/racedbapp/result/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_health_gated(gated_client, user):
    response = gated_client.get("/health/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_authenticated_user_gets_content(gated_client, user):
    gated_client.login(username="tester", password="pw")
    response = gated_client.get("/index/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_middleware_not_attached_when_settings_not_dev(user):
    # SETTINGS is unset under pytest: the gate must not be in MIDDLEWARE.
    from django.conf import settings

    assert "racedbapp.middleware.QaAuthGateMiddleware" not in settings.MIDDLEWARE
    client = Client()
    response = client.get("/index/")
    assert response.status_code != 401


@pytest.mark.django_db
def test_garbage_session_cookie_still_401(gated_client, user):
    gated_client.cookies["sessionid"] = "forged-value"
    response = gated_client.get("/index/")
    assert response.status_code == 401
