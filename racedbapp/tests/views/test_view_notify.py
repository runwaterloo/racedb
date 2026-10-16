"""Tests for the /notify endpoint's response contract (issue #365).

The endpoint is hit by a Google Sheets trigger and by humans with curl:

- 200 only when the import fully succeeds, body reports counts
- 422 when the sheet data is invalid, body explains what was wrong
  (and mentions that individuals were imported, if they were)
"""
import datetime

import pytest
from django.core.management import call_command  # noqa: F401 (used via view)
from django.test import Client

from racedbapp.models import Category, Config, Result, Teamcategory, Teamresult


@pytest.fixture
def notifykey(db):
    Config.objects.bulk_create([Config(name="notifykey", value="secret")])


def individual_row(**overrides):
    """One individual result row as it would come from a Google Sheet."""
    row = {
        "place": 1,
        "bib": "123",
        "athlete": "Fast Runner",
        "guntime": "0:20:00",
        "gender": "F",
        "age": 25,
        "category": "F25-29",
        "chiptime": "0:19:19",
        "city": "Waterloo",
    }
    row.update(overrides)
    return row


def team_row(**overrides):
    """One team result row as it would come from a Google Sheet."""
    row = {
        "team_category": "Open",
        "team_place": 1,
        "team_name": "Fast Team",
        "athlete_team_place": 1,
        "athlete_time": "20:00",
        "athlete_name": "Fast Runner",
        "counts": "TRUE",
        "estimated": "FALSE",
    }
    row.update(overrides)
    return row


def import_results(event, individual=(), team=()):
    """Import fake google results for event by calling the /notify view.

    Returns the response.
    """
    fake_results = {"individual": list(individual), "team": list(team)}
    event.resultsurl = "https://docs.google.com/fake"
    event.save()
    for row in fake_results["individual"]:
        Category.objects.get_or_create(name=row.get("category", ""))
    from unittest import mock

    with mock.patch(
        "racedbapp.management.commands.addraces.get_results_from_google",
        return_value=fake_results,
    ), mock.patch(
        "racedbapp.management.commands.addraces.tasks.clear_cache.delay"
    ):
        response = Client().get("/notify?notifykey=secret&event_id=" + str(event.id))
    return response


@pytest.mark.django_db
def test_notify_success_returns_200_with_counts(
    notifykey, create_event, create_category
):
    event = create_event()
    create_category(name_suffix="f2529", is_masters=False)
    from racedbapp.models import Category

    category = Category.objects.get(name="Test Category f2529")
    row = individual_row(category=category.name)
    response = import_results(event, individual=[row], team=[])
    assert response.status_code == 200
    assert "1 results processed" in response.content.decode()
    assert "Process complete" in response.content.decode()


@pytest.mark.django_db
def test_notify_invalid_team_data_returns_422_with_message(
    notifykey, create_event, create_category
):
    """A team category that does not exist is invalid data -> 422."""
    event = create_event()
    row = team_row(team_category="No Such Category")
    response = import_results(event, individual=[individual_row()], team=[row])
    assert response.status_code == 422
    body = response.content.decode()
    assert "No Such Category" in body
    assert "Individual results" in body  # individuals did import
    assert Result.objects.filter(event=event).count() == 1
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_notify_invalid_team_data_keeps_old_team_results(
    notifykey, create_event, create_category
):
    """When team data is invalid, previously imported team results stay."""
    event = create_event()
    tc = Teamcategory.objects.create(name="Open", slug="open", sortorder=1)
    Teamresult.objects.create(
        event=event,
        team_category=tc,
        team_place=1,
        team_name="Old Team",
        athlete_team_place=1,
        athlete_time=datetime.timedelta(minutes=20),
        athlete_name="Old Runner",
        counts=True,
    )
    row = team_row(team_category="No Such Category")
    response = import_results(event, individual=[individual_row()], team=[row])
    assert response.status_code == 422
    assert Teamresult.objects.filter(event=event, team_name="Old Team").exists()


@pytest.mark.django_db
def test_notify_team_category_without_place_1_is_rejected(
    notifykey, create_event, create_category
):
    """A category with counts=True rows but no team_place=1 is the bug
    behind issue #365 -> 422."""
    event = create_event()
    Teamcategory.objects.create(name="Open", slug="open", sortorder=1)
    rows = [
        team_row(team_place=2, team_name="Second Team", athlete_name="A"),
        team_row(team_place=3, team_name="Third Team", athlete_name="B"),
    ]
    response = import_results(event, individual=[individual_row()], team=rows)
    assert response.status_code == 422
    assert "team_place" in response.content.decode() or "place 1" in response.content.decode()
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_notify_invalid_team_time_returns_422(
    notifykey, create_event, create_category
):
    event = create_event()
    Teamcategory.objects.create(name="Open", slug="open", sortorder=1)
    row = team_row(athlete_time="not-a-time")
    response = import_results(event, individual=[individual_row()], team=[row])
    assert response.status_code == 422
    assert "not-a-time" in response.content.decode()


@pytest.mark.django_db
def test_notify_individual_all_or_nothing(notifykey, create_event, create_category):
    """If one individual row is invalid, no individual rows are imported."""
    event = create_event()
    good_row = individual_row(place=1, athlete="Good Runner")
    bad_row = individual_row(place=2, athlete="Bad Runner", guntime="not-a-time")
    response = import_results(event, individual=[good_row, bad_row])
    assert response.status_code == 422
    assert "not-a-time" in response.content.decode()
    assert Result.objects.filter(event=event).count() == 0
