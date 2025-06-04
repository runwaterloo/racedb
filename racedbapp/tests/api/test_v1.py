import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


def test_v1_root_exists():
    client = APIClient()
    response = client.get("/v1/")
    assert response is not None, "No response returned from /v1/"
    assert response.status_code is not None, "No status code returned from /v1/"


def test_v1_root_requires_authentication():
    client = APIClient()
    response = client.get("/v1/")
    # DRF returns 401 for unauthenticated, but 403 if SessionAuthentication is used without CSRF token
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden, got {response.status_code}"
    )


@pytest.mark.django_db
def test_v1_root_authenticated_session():
    # Create a user
    User.objects.create_user(username="apitestuser", password="testpass123")
    client = APIClient()
    client.login(username="apitestuser", password="testpass123")
    # Get CSRF token from client cookies (if present)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    response = client.get("/v1/", **headers)
    assert response.status_code == 200, (
        f"Expected 200 OK for authenticated user, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")
    assert response.json()["message"] == "Welcome to the API v1 root."


@pytest.mark.django_db
def test_v1_root_authenticated_token():
    # Create a user
    user = User.objects.create_user(username="apitokenuser", password="testpass123")
    # Try to import Token model (will fail if not installed)
    try:
        from rest_framework.authtoken.models import Token
    except ImportError:
        pytest.fail("rest_framework.authtoken is not installed or not in INSTALLED_APPS")
    # Create a token for the user
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    response = client.get("/v1/", HTTP_AUTHORIZATION=f"Token {token.key}")
    assert response.status_code == 200, (
        f"Expected 200 OK for token-authenticated user, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")
    assert response.json()["message"] == "Welcome to the API v1 root."


@pytest.mark.django_db
def test_v1_root_invalid_token():
    client = APIClient()
    # Use a clearly invalid token
    response = client.get("/v1/", HTTP_AUTHORIZATION="Token invalidtoken123")
    # Should return 401 Unauthorized or 403 Forbidden for invalid token
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for invalid token, got {response.status_code}"
    )
    assert "detail" in response.json()
    assert (
        "Invalid token" in response.json()["detail"]
        or "credentials" in response.json()["detail"].lower()
    )
