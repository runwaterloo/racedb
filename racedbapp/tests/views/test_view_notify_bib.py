"""Tests for bib-mode team importing via the /notify endpoint.

When the team tab carries a bib column, all Teamresult fields are
computed from the event's individual results joined on bib. Team
problems never block individual results (issue #365 contract).
"""

import datetime

import pytest
from django.test import Client

from racedbapp.models import (
    Category,
    Config,
    Result,
    Teamcategory,
    Teamresult,
)


@pytest.fixture
def notifykey(db):
    Config.objects.bulk_create([Config(name="notifykey", value="secret")])


def individual_row(**overrides):
    row = {
        "place": 1,
        "bib": "101",
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
    row = {"bib": "101", "team_name": "Fast Team", "team_category": "Open"}
    row.update(overrides)
    return row


def make_categories(counts=3):
    Teamcategory.objects.create(name="Open", slug="open", sortorder=1, counts=counts)
    Teamcategory.objects.create(name="Spouse", slug="spouse", sortorder=2, counts=2)


def import_results(event, individual=(), team=()):
    fake_results = {"individual": list(individual), "team": list(team)}
    event.resultsurl = "https://docs.google.com/fake"
    event.save()
    for row in fake_results["individual"]:
        Category.objects.get_or_create(name=row.get("category", ""))
    from unittest import mock

    with (
        mock.patch(
            "racedbapp.management.commands.addraces.get_results_from_google",
            return_value=fake_results,
        ),
        mock.patch("racedbapp.management.commands.addraces.tasks.clear_cache.delay"),
    ):
        response = Client().get("/notify?notifykey=secret&event_id=" + str(event.id))
    return response


@pytest.mark.django_db
def test_bib_mode_imports_and_scores_team(notifykey, create_event, create_category):
    """counting runners are the fastest-by-guntime; team place by summed guntime."""
    event = create_event()
    make_categories(counts=3)
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:22:00"),
        individual_row(place=4, bib="104", athlete="D", guntime="0:23:00"),
    ]
    team = [
        team_row(bib="103", team_name="Team 1"),
        team_row(bib="101", team_name="Team 1"),
        team_row(bib="102", team_name="Team 1"),
        team_row(bib="104", team_name="Team 1"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert "team results processed (bib mode)" in response.content.decode()
    results = Teamresult.objects.filter(event=event).order_by("athlete_team_place")
    assert results.count() == 4
    # top 3 by guntime count; 4th is a non-counter
    counted = list(results.filter(counts=True))
    assert [r.athlete_name for r in counted] == ["A", "B", "C"]
    assert counted[0].athlete_team_place == 1
    noncount = results.get(athlete_name="D")
    assert noncount.counts is False
    assert noncount.athlete_team_place == 4
    team_place = counted[0].team_place
    assert results.filter(team_name="Team 1", team_place=team_place).count() == 4


@pytest.mark.django_db
def test_bib_mode_team_place_by_sum_guntime(notifykey, create_event, create_category):
    """Team place = sum of counting runners' guntime, lower wins."""
    event = create_event()
    make_categories(counts=2)
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:30:00"),
        individual_row(place=4, bib="104", athlete="D", guntime="0:31:00"),
    ]
    team = [
        team_row(bib="101", team_name="Fast Team"),
        team_row(bib="103", team_name="Fast Team"),
        team_row(bib="102", team_name="Slow Team"),
        team_row(bib="104", team_name="Slow Team"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert (
        Teamresult.objects.get(event=event, team_name="Fast Team", athlete_team_place=1).team_place
        == 1
    )
    assert (
        Teamresult.objects.get(event=event, team_name="Slow Team", athlete_team_place=1).team_place
        == 2
    )


@pytest.mark.django_db
def test_bib_mode_guntime_tie_broken_by_last_counter_place(
    notifykey, create_event, create_category
):
    """Equal summed guntime -> better overall place of the last counting
    runner wins."""
    event = create_event()
    make_categories(counts=2)
    individuals = [
        # sums: Team A = 20:00+22:00 = 42:00; Team B = 21:00+21:00 = 42:00
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:21:00"),
        individual_row(place=4, bib="104", athlete="D", guntime="0:22:00"),
    ]
    team = [
        team_row(bib="101", team_name="Team A"),
        team_row(bib="104", team_name="Team A"),
        team_row(bib="102", team_name="Team B"),
        team_row(bib="103", team_name="Team B"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    # Team B's last counter (bib 103, place 3) beats Team A's (bib 104, place 4)
    assert (
        Teamresult.objects.get(event=event, team_name="Team B", athlete_team_place=1).team_place
        == 1
    )
    assert (
        Teamresult.objects.get(event=event, team_name="Team A", athlete_team_place=1).team_place
        == 2
    )


@pytest.mark.django_db
def test_bib_mode_too_few_finishers_skips_team(notifykey, create_event, create_category):
    """A team with fewer counting-eligible finishers than counts is skipped."""
    event = create_event()
    make_categories(counts=3)
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
    ]
    team = [
        team_row(bib="101", team_name="Small Team"),
        team_row(bib="102", team_name="Small Team"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert "Small Team" in response.content.decode()
    assert "team skipped" in response.content.decode()
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_bib_mode_bib_not_found_is_warning_not_error(notifykey, create_event, create_category):
    """A bib in the team tab with no individual result is skipped with a
    warning; the import still returns 200."""
    event = create_event()
    make_categories(counts=3)
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:22:00"),
    ]
    team = [
        team_row(bib="101", team_name="Team 1"),
        team_row(bib="102", team_name="Team 1"),
        team_row(bib="103", team_name="Team 1"),
        team_row(bib="999", team_name="Team 1"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert (
        "bib 999 on team Team 1 (Open): not found in individual results"
        in response.content.decode()
    )
    assert Teamresult.objects.filter(event=event).count() == 3


@pytest.mark.django_db
def test_bib_mode_nonfinisher_bib_is_skipped_with_warning(notifykey, create_event, create_category):
    """A team bib matching a DQ/DNF/DNS runner is treated as if not there."""
    event = create_event()
    make_categories(counts=3)
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:22:00"),
        # DQ'd runner (place >= 990000)
        individual_row(place=990001, bib="104", athlete="D", guntime="99:00:00"),
    ]
    team = [
        team_row(bib="101", team_name="Team 1"),
        team_row(bib="102", team_name="Team 1"),
        team_row(bib="103", team_name="Team 1"),
        team_row(bib="104", team_name="Team 1"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert "non-finisher" in response.content.decode()
    # only 3 real runners count; the DQ runner is invisible to the team
    assert Teamresult.objects.filter(event=event).count() == 3


@pytest.mark.django_db
def test_bib_mode_unknown_category_aborts_team_processing(notifykey, create_event, create_category):
    """An unknown team category aborts all team processing (422), while
    individuals still import."""
    event = create_event()
    make_categories()
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
    ]
    team = [
        team_row(bib="101", team_name="Team 1", team_category="Open"),
        team_row(bib="101", team_name="Team 1", team_category="Opne"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 422
    body = response.content.decode()
    assert "Opne" in body
    assert "Individual results" in body
    assert Result.objects.filter(event=event).count() == 1
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_bib_mode_counts_must_be_positive_integer(notifykey, create_event, create_category):
    """counts of None or <= 0 is a hard error."""
    event = create_event()
    Teamcategory.objects.create(name="Open", slug="open", sortorder=1, counts=0)
    response = import_results(
        event,
        individual=[individual_row()],
        team=[team_row()],
    )
    assert response.status_code == 422
    body = response.content.decode()
    # Django escapes > in HTML output
    assert "counts must be an integer" in body
    assert "&gt; 0" in body
    assert "Import Partial Success" in body
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_bib_mode_duplicate_bib_in_category_is_hard_error(notifykey, create_event, create_category):
    event = create_event()
    make_categories()
    response = import_results(
        event,
        individual=[individual_row()],
        team=[
            team_row(bib="101", team_name="Team 1"),
            team_row(bib="101", team_name="Team 2"),
        ],
    )
    assert response.status_code == 422
    assert "duplicate bib 101" in response.content.decode()
    assert Teamresult.objects.filter(event=event).count() == 0


@pytest.mark.django_db
def test_bib_mode_same_bib_in_two_categories_allowed(notifykey, create_event, create_category):
    """The same bib may appear in more than one team category."""
    event = create_event()
    make_categories()
    response = import_results(
        event,
        individual=[individual_row()],
        team=[
            team_row(bib="101", team_name="Team 1", team_category="Open"),
            team_row(bib="101", team_name="Team 1", team_category="Spouse"),
        ],
    )
    assert response.status_code == 200
    assert Teamresult.objects.filter(event=event).count() == 2


@pytest.mark.django_db
def test_bib_mode_old_team_results_replaced(notifykey, create_event, create_category):
    """A successful bib-mode import replaces existing team results."""
    event = create_event()
    make_categories()
    old = Teamcategory.objects.get(name="Open")
    Teamresult.objects.create(
        event=event,
        team_category=old,
        team_place=1,
        team_name="Old Team",
        athlete_team_place=1,
        athlete_time=datetime.timedelta(minutes=20),
        athlete_name="Old Runner",
        counts=True,
    )
    individuals = [
        individual_row(place=1, bib="101", athlete="A", guntime="0:20:00"),
        individual_row(place=2, bib="102", athlete="B", guntime="0:21:00"),
        individual_row(place=3, bib="103", athlete="C", guntime="0:22:00"),
    ]
    team = [
        team_row(bib="101", team_name="New Team"),
        team_row(bib="102", team_name="New Team"),
        team_row(bib="103", team_name="New Team"),
    ]
    response = import_results(event, individual=individuals, team=team)
    assert response.status_code == 200
    assert not Teamresult.objects.filter(event=event, team_name="Old Team").exists()
    assert Teamresult.objects.filter(event=event, team_name="New Team").count() == 3
