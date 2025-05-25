def test_events_results_exist(authenticated_client, create_event, create_result):
    client, headers = authenticated_client
    event = create_event()
    response = client.get(f"/v1/events/{event.id}/", **headers)
    data = response.json()
    results_exist = data.get("results_exist")
    assert results_exist is False, "Results exist should be False when no results are present"
    create_result(event=event)
    response = client.get(f"/v1/events/{event.id}/", **headers)
    data = response.json()
    results_exist = data.get("results_exist")
    assert results_exist is True, "Results exist should be True when results are present"


def test_events_sorted_by_date(authenticated_client, create_event):
    client, headers = authenticated_client
    create_event(date="2025-01-01", name_suffix="a")
    create_event(date="2025-01-02", name_suffix="b")
    response = client.get("/v1/events/", **headers)
    data = response.json()
    first_date = data["results"][0]["date"]
    assert first_date == "2025-01-02", "Events should be sorted by date, latest first"


def test_events_filtering(
    authenticated_client, create_distance, create_race, create_event, create_category, create_result
):
    client, headers = authenticated_client
    distance1 = create_distance(name_suffix="first", km=1)
    distance2 = create_distance(name_suffix="second", km=2)
    race1 = create_race(name_suffix="first")
    race2 = create_race(name_suffix="second")
    event1 = create_event(distance=distance1, race=race1, date="2025-01-01")
    create_event(distance=distance2, race=race2, date="2026-01-01")
    create_result(event=event1)

    # Filter by year
    response = client.get(f"/v1/events/?year={event1.date.year}", **headers)
    data = response.json()
    mismatches = [
        r["date"] for r in data["results"] if not r["date"].startswith(str(event1.date.year))
    ]
    assert not mismatches, (
        f"Found events with date(s) not matching year filter {event1.date.year}: {mismatches}"
    )

    # Filter by distance
    response = client.get(f"/v1/events/?distance_slug={distance1.slug}", **headers)
    data = response.json()
    mismatches = [
        r["distance_slug"] for r in data["results"] if r["distance_slug"] != distance1.slug
    ]
    assert not mismatches, (
        f"Found events with distance_slug(s) not matching filter {distance1.slug}: {mismatches}"
    )

    # Filter by race
    response = client.get(f"/v1/events/?race_slug={race1.slug}", **headers)
    data = response.json()
    mismatches = [r["race_slug"] for r in data["results"] if r["race_slug"] != race1.slug]
    assert not mismatches, (
        f"Found events with race_slug(s) not matching filter {race1.slug}: {mismatches}"
    )

    # Filter by results_exist
    response = client.get("/v1/events/?results_exist=true", **headers)
    data = response.json()
    mismatches = [r["results_exist"] for r in data["results"] if not r["results_exist"]]
    assert not mismatches, (
        "Found events with results_exist == False when filtering for results_exist=true"
    )
    response = client.get("/v1/events/?results_exist=false", **headers)
    data = response.json()
    mismatches = [r["results_exist"] for r in data["results"] if r["results_exist"]]
    assert not mismatches, (
        "Found events with results_exist == True when filtering for results_exist=false"
    )
    response = client.get("/v1/events/?results_exist=notboolean", **headers)
    data = response.json()
    assert response.status_code == 200
