import pytest
from rest_framework.test import APIClient


def test_endpoint_exists():
    url = "/v1/"
    client = APIClient()
    response = client.get(url)
    assert response is not None, f"No response returned from {url}"
    assert response.status_code is not None, f"No status code returned from {url}"


def test_endpoint_requires_authentication():
    url = "/v1/"
    client = APIClient()
    response = client.get(url)
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for {url}, got {response.status_code}"
    )


@pytest.mark.django_db
def test_endpoint_authenticated_session(test_user):
    url = "/v1/"
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
def test_endpoint_authenticated_token(test_user):
    url = "/v1/"
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
def test_endpoint_invalid_token():
    url = "/v1/"
    client = APIClient()
    response = client.get(url, HTTP_AUTHORIZATION="Token invalidtoken123")
    assert response.status_code in (401, 403), (
        f"Expected 401 Unauthorized or 403 Forbidden for invalid token on {url}, got {response.status_code}"
    )
    assert "detail" in response.json()
    assert "login_url" in response.json()


@pytest.mark.django_db
def test_endpoint_is_readonly():
    url = "/v1/"
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
