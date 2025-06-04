from rest_framework.test import APIClient


def test_v1_root():
    client = APIClient()
    response = client.get("/v1/")
    assert response.status_code == 200
    assert response["content-type"].startswith("application/json")
    assert response.json()["message"] == "Welcome to the API v1 root."
