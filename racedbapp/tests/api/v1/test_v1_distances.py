def test_distances_list_returns_results(authenticated_client, create_distance):
    create_distance()
    client, headers = authenticated_client
    response = client.get("/v1/distances/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list), "Expected a list of results"
    assert len(data["results"]) > 0, "Expected at least one result in the response"


def test_distances_list_fields(authenticated_client, create_distance):
    create_distance()
    client, headers = authenticated_client
    response = client.get("/v1/distances/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "next" in data
    assert "previous" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    result = data["results"][0]
    expected_fields = {
        "id",
        "slug",
        "name",
        "km",
        "showrecord",
    }
    assert set(result.keys()) == expected_fields
