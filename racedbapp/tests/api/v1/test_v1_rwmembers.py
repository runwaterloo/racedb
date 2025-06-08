def test_inactive_members_not_returned(authenticated_client, create_rwmember):
    client, headers = authenticated_client
    create_rwmember(active=False)
    response = client.get("/v1/rwmembers/", **headers)
    data = response.json()
    assert len(data["results"]) == 0, "Should not return inactive members"
