import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

ENDPOINTS = ["/v1/", "/v1/results/"]


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_exists(endpoint):
    client = APIClient()
    response = client.get(endpoint)
    assert response is not None, f"No response returned from {endpoint}"
    assert response.status_code is not None, f"No status code returned from {endpoint}"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_requires_authentication(endpoint):
    client = APIClient()
    response = client.get(endpoint)
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for {endpoint}, got {response.status_code}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_authenticated_session(endpoint):
    username = "apitestuser"
    password = "testpass123"
    User.objects.create_user(username=username, password=password)
    client = APIClient()
    client.login(username=username, password=password)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    response = client.get(endpoint, **headers)
    assert response.status_code == 200, (
        f"Expected 200 OK for authenticated user on {endpoint}, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_authenticated_token(endpoint):
    user = User.objects.create_user(username="apitokenuser", password="testpass123")
    try:
        from rest_framework.authtoken.models import Token
    except ImportError:
        pytest.fail("rest_framework.authtoken is not installed or not in INSTALLED_APPS")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    response = client.get(endpoint, HTTP_AUTHORIZATION=f"Token {token.key}")
    assert response.status_code == 200, (
        f"Expected 200 OK for token-authenticated user on {endpoint}, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_invalid_token(endpoint):
    client = APIClient()
    response = client.get(endpoint, HTTP_AUTHORIZATION="Token invalidtoken123")
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for invalid token on {endpoint}, got {response.status_code}"
    )
    assert "detail" in response.json()
    assert (
        "Invalid token" in response.json()["detail"]
        or "credentials" in response.json()["detail"].lower()
    )


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_endpoint_is_readonly(endpoint):
    client = APIClient()
    # Test POST
    response = client.post(endpoint, {})
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for POST on {endpoint}, got {response.status_code}"
    )
    # Test PUT
    response = client.put(endpoint, {})
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for PUT on {endpoint}, got {response.status_code}"
    )
    # Test DELETE
    response = client.delete(endpoint)
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for DELETE on {endpoint}, got {response.status_code}"
    )
