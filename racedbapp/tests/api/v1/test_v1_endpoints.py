import json
import os

import pytest
from rest_framework.test import APIClient

# Load endpoint definitions from JSON file
with open(os.path.join(os.path.dirname(__file__), "endpoints.json")) as f:
    ENDPOINTS = json.load(f)


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_exists(endpoint):
    url = endpoint["url"]
    client = APIClient()
    response = client.get(url)
    assert response is not None, f"No response returned from {url}"
    assert response.status_code is not None, f"No status code returned from {url}"


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_requires_authentication(endpoint):
    url = endpoint["url"]
    client = APIClient()
    response = client.get(url)
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for {url}, got {response.status_code}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_authenticated_session(endpoint, test_user):
    url = endpoint["url"]
    _user, username, password = test_user
    client = APIClient()
    client.login(username=username, password=password)
    csrf_token = client.cookies.get("csrftoken")
    headers = {}
    if csrf_token:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token.value
    response = client.get(url, **headers)
    assert response.status_code == 200, (
        f"Expected 200 OK for authenticated user on {url}, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_authenticated_token(endpoint, test_user):
    url = endpoint["url"]
    user, _username, _password = test_user
    try:
        from rest_framework.authtoken.models import Token
    except ImportError:
        pytest.fail("rest_framework.authtoken is not installed or not in INSTALLED_APPS")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    response = client.get(url, HTTP_AUTHORIZATION=f"Token {token.key}")
    assert response.status_code == 200, (
        f"Expected 200 OK for token-authenticated user on {url}, got {response.status_code}"
    )
    assert response["content-type"].startswith("application/json")


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_invalid_token(endpoint):
    url = endpoint["url"]
    client = APIClient()
    response = client.get(url, HTTP_AUTHORIZATION="Token invalidtoken123")
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for invalid token on {url}, got {response.status_code}"
    )
    assert "detail" in response.json()
    assert (
        "Invalid token" in response.json()["detail"]
        or "credentials" in response.json()["detail"].lower()
    )


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e["url"] for e in ENDPOINTS])
def test_endpoint_is_readonly(endpoint):
    url = endpoint["url"]
    client = APIClient()
    # Test POST
    response = client.post(url, {})
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for POST on {url}, got {response.status_code}"
    )
    # Test PUT
    response = client.put(url, {})
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for PUT on {url}, got {response.status_code}"
    )
    # Test DELETE
    response = client.delete(url)
    assert response.status_code in (403, 405), (
        f"Expected 403 Forbidden or 405 Method Not Allowed for DELETE on {url}, got {response.status_code}"
    )
