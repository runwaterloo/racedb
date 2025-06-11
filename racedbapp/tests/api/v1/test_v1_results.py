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
