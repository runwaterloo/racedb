from racedbapp.shared import shared


def test_set_distance_display_name(create_distance, create_sequel):
    # Create a distance and a sequel
    distance = create_distance()
    original_name = distance.name

    # Check display name is correct (no sequel)
    shared.set_distance_display_name(distance, None)
    assert distance.display_name == original_name

    # Check display name is correct (with sequel)
    sequel = create_sequel(name="Sequel Name")
    shared.set_distance_display_name(distance, sequel)
    assert distance.display_name == sequel.name
