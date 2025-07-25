import pytest
from django.core.exceptions import ValidationError

from racedbapp.models import Sequel


@pytest.mark.django_db
def test_sequel_creation(create_sequel):
    sequel = create_sequel(name="My Sequel Name")
    sequel.clean()
    assert str(sequel) == "My Sequel Name"


@pytest.mark.django_db
def test_sequel_slug_team_not_allowed():
    sequel = Sequel(name="Test Sequel", slug="team")
    with pytest.raises(ValidationError) as excinfo:
        sequel.clean()
    assert "team" in str(excinfo.value)


@pytest.mark.django_db
def test_event_with_null_sequel(create_event):
    event = create_event()
    assert event.sequel is None


@pytest.mark.django_db
def test_event_with_non_null_sequel(create_event, create_sequel):
    sequel = create_sequel()
    event = create_event(sequel=sequel)
    assert event.sequel == sequel


@pytest.mark.django_db
def test_event_unique_constraint(create_distance, create_event, create_race, create_sequel):
    distance = create_distance()
    race = create_race()

    # test that two events cannot have the same year, distance, race, and (null) sequel
    event1 = create_event(date="2025-01-01", distance=distance, race=race)
    event2 = create_event(date="2025-01-02", distance=distance, race=race)
    with pytest.raises(ValidationError):
        event2.clean()

    # test that two events cannot have the same year, distance, race and sequel
    sequel = create_sequel()
    event1.sequel = sequel
    event1.save()
    event2.sequel = sequel
    with pytest.raises(ValidationError):
        event2.clean()
