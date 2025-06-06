def test_results_list_returns_results(authenticated_client, create_result):
    client, headers = authenticated_client
    create_result()
    response = client.get("/v1/results/", **headers)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list), "Expected a list of results"
    assert len(data["results"]) > 0, "Expected at least one result in the response"


def test_results_list_fields(authenticated_client, create_result):
    client, headers = authenticated_client
    create_result()
    response = client.get("/v1/results/", **headers)
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
        "event",
        "place",
        "bib",
        "athlete",
        "rwmember",
        "gender",
        "gender_place",
        "category",
        "category_place",
        "age",
        "chiptime",
        "guntime",
        "city",
        "province",
        "country",
        "division",
        "isrwpb",
    }
    assert set(result.keys()) == expected_fields


def test_results_filter_by_event(
    authenticated_client, create_distance, create_race, create_event, create_category, create_result
):
    client, headers = authenticated_client
    race = create_race()
    distance1 = create_distance(name_suffix="first", km=1)
    distance2 = create_distance(name_suffix="second", km=2)
    event1 = create_event(distance=distance1, race=race, name_suffix="first")
    event2 = create_event(distance=distance2, race=race, name_suffix="second")
    category = create_category()
    create_result(event=event1, category=category, place=1)
    create_result(event=event2, category=category, place=2)
    # Filter by the first event (should only return results for event1.id)
    response = client.get(f"/v1/results/?event={event1.id}", **headers)
    data = response.json()
    assert all(r["event"] == event1.id for r in data["results"])
    # Filter by the second event (should only return results for event2.id)
    response = client.get(f"/v1/results/?event={event2.id}", **headers)
    data = response.json()
    assert all(r["event"] == event2.id for r in data["results"])


def test_results_are_sorted_by_place_within_event(
    authenticated_client, create_event, create_result
):
    client, headers = authenticated_client
    event = create_event()
    create_result(event=event, name_suffix="a", place=3)
    create_result(event=event, name_suffix="b", place=2)
    create_result(event=event, name_suffix="c", place=1)
    response = client.get(f"/v1/results/?event={event.id}", **headers)
    data = response.json()
    places = [result["place"] for result in data["results"]]
    assert places == sorted(places), "Results are not sorted by place"
