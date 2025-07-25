import pytest
from django.core.exceptions import ValidationError

from racedbapp.models import Sequel


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
def test_event_unique_constraint(create_event, create_sequel):
    sequel = create_sequel()
    create_event(sequel=sequel)
    with pytest.raises(Exception):
        create_event(sequel=sequel)
