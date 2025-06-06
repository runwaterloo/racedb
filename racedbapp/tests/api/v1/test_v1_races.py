def test_races_list_returns_results(authenticated_client, create_race):
    create_race()
    client, headers = authenticated_client
    response = client.get("/v1/races/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list), "Expected a list of results"
    assert len(data["results"]) > 0, "Expected at least one result in the response"


def test_races_list_fields(authenticated_client, create_race):
    create_race()
    client, headers = authenticated_client
    response = client.get("/v1/races/", **headers)
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
        "name",
        "shortname",
        "slug",
    }
    assert set(result.keys()) == expected_fields
