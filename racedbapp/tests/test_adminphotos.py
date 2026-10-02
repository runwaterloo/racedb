import pytest

from racedbapp.models import Config


@pytest.mark.django_db
def test_adminphotos_distinguishes_sequel_event(
    authenticated_client,
    create_category,
    create_distance,
    create_event,
    create_race,
    create_result,
    create_sequel,
):
    client, _headers = authenticated_client
    Config.objects.bulk_create([Config(name="notifykey", value="test-notify-key")])
    race = create_race(name_suffix="adminphotos")
    race.shortname = "Race Short"
    race.save()
    distance = create_distance(name_suffix="adminphotos")
    sequel = create_sequel(name="Stage Two", slug="stage-two")
    main_event = create_event(date="2025-01-01", race=race, distance=distance)
    sequel_event = create_event(date="2025-01-01", race=race, distance=distance, sequel=sequel)
    main_event.flickrsetid = 1
    main_event.save()
    sequel_event.flickrsetid = 2
    sequel_event.save()
    create_result(event=main_event, category=create_category(name_suffix="main"))
    create_result(event=sequel_event, category=create_category(name_suffix="sequel"))

    response = client.get("/adminphotos/")

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        '<a href="/event/2025/test-race-adminphotos/test-distance-adminphotos">2025 Race Short Test Distance adminphotos</a>'
        in content
    )
    assert 'href="/event/2025/test-race-adminphotos/test-distance-adminphotos/stage-two"' in content
    assert ">2025 Race Short Test Distance adminphotos stage-two</a>" in content
