"""Tests for the public (secret-free) Google Sheet fetch path."""
from pathlib import Path
from unittest import mock

import datetime

from django.core.management import call_command

from racedbapp.management.commands.addraces import (
    fetch_public_sheet,
    get_results_from_google,
)
from racedbapp.models import Event, Result, Teamresult

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _mock_response(text):
    response = mock.Mock()
    response.text = text
    response.raise_for_status = mock.Mock()
    return response


def _fixture(tab):
    return (FIXTURES_DIR / f"import_test_{tab}.csv").read_text()


def _mock_requests():
    """Patch requests.get to serve the fixture CSVs for each tab."""
    def fake_get(url, timeout=None):
        if "sheet=individual" in url:
            return _mock_response(_fixture("individual"))
        if "sheet=team" in url:
            return _mock_response(_fixture("team"))
        raise AssertionError(f"Unexpected url: {url}")

    return mock.patch(
        "racedbapp.management.commands.addraces.requests.get", side_effect=fake_get
    )


def test_fetch_public_sheet_coercion():
    """Values are coerced like gspread get_all_records: numbers, booleans, rest strings."""
    with _mock_requests():
        records = fetch_public_sheet(
            "https://docs.google.com/spreadsheets/d/fake_sheet_id/edit", "team"
        )
    assert records[0] == {
        "team_category": "Open",
        "team_place": 1,
        "team_name": "Open Team 1",
        "athlete_team_place": 1,
        "athlete_time": "00:21:10",
        "athlete_name": "Open 1 Runner 1",
        "counts": True,
        "estimated": False,
    }
    # the leading-zero time from the sheet must survive as a string
    assert all(isinstance(r["athlete_time"], str) for r in records)


def test_get_results_from_google_falls_back_without_service_account():
    """With no service-account file, the public gviz endpoint is used for both tabs."""
    with mock.patch(
        "racedbapp.management.commands.addraces.os.path.exists", return_value=False
    ), _mock_requests():
        results = get_results_from_google(
            "https://docs.google.com/spreadsheets/d/fake_sheet_id/edit"
        )
    assert set(results) == {"individual", "team"}
    assert results["individual"][0]["athlete"] == "Open 1 Runner 1"
    assert results["team"][0]["team_name"] == "Open Team 1"


def test_get_results_from_google_uses_service_account_when_present():
    """When the service-account file exists, the gspread path is used (unchanged)."""
    gspread_service_account = mock.Mock()
    worksheet = mock.Mock()
    worksheet.get_all_records.return_value = [{"athlete": "SA Runner"}]
    sheet = mock.Mock()
    sheet.worksheet.return_value = worksheet
    sheet.worksheets.return_value = [mock.Mock(title="individual"), mock.Mock(title="team")]
    gspread_service_account.return_value.open_by_url.return_value = sheet
    with mock.patch(
        "racedbapp.management.commands.addraces.os.path.exists", return_value=True
    ), mock.patch(
        "racedbapp.management.commands.addraces.gspread.service_account",
        gspread_service_account,
    ):
        results = get_results_from_google(
            "https://docs.google.com/spreadsheets/d/fake_sheet_id/edit"
        )
    assert results["individual"] == [{"athlete": "SA Runner"}]
    assert results["team"] == [{"athlete": "SA Runner"}]


def test_full_import_from_fixture_csvs(db):
    """End-to-end: addraces over the fixture sheets imports individuals and teams."""
    call_command("flush", interactive=False)
    call_command(
        "loaddata", "race", "distance", "sequel", "event", "series", "config",
        "teamcategory",
    )
    event = Event.objects.get(pk=26)
    assert event.race.name == "Import Test Race"
    # Import Test 5 KM sits between the 2023 Waterloo Classic (2023-06-18)
    # and the 2023 Fall Classic (2023-10-22)
    assert event.date == datetime.date(2023, 8, 19)

    with _mock_requests(), mock.patch(
        "racedbapp.management.commands.addraces.tasks.clear_cache.delay"
    ):
        call_command("addraces", event_id=event.id)

    individual = Result.objects.filter(event=event)
    team = Teamresult.objects.filter(event=event)
    assert individual.count() == 40  # 36 team athletes + 5 independent runners
    assert team.count() == 36
    top = individual.order_by("place").first()
    assert top.athlete == "Open 1 Runner 1"
    import datetime as _dt
    assert top.guntime == _dt.timedelta(seconds=1270)
    # both tied Open teams are team_place 1
    places = sorted(
        set(
            Teamresult.objects.filter(
                event=event, team_category__name="Open"
            ).values_list("team_place", flat=True)
        )
    )
    assert places[0] == 1 and places[1] == 3
    # fixture athlete renamed to match the auto-created Rwmember
    assert Result.objects.filter(event=event, athlete="Import Test Member 1").exists()
    # one runner appears on both an Open and a Spouse team
    dual = Teamresult.objects.filter(event=event, athlete_name="Spouse 1 Runner 1")
    assert sorted(dual.values_list("team_category__name", flat=True)) == [
        "Open",
        "Spouse",
    ]


def test_team_import_accepts_gspread_string_booleans(db):
    """Prod path (gspread) yields counts/estimated as \"TRUE\" strings; team
    import must treat them the same as the boolean True the public fetch gives."""
    call_command("flush", interactive=False)
    call_command(
        "loaddata", "race", "distance", "sequel", "event", "series", "config",
        "teamcategory",
    )
    event = Event.objects.get(pk=26)
    import csv, io

    fake_results = {
        tab: list(csv.DictReader(io.StringIO(_fixture(tab))))
        for tab in ("individual", "team")
    }
    with mock.patch(
        "racedbapp.management.commands.addraces.get_results_from_google",
        return_value=fake_results,
    ), mock.patch(
        "racedbapp.management.commands.addraces.tasks.clear_cache.delay"
    ):
        call_command("addraces", event_id=event.id)
    team = Teamresult.objects.filter(event=event)
    assert team.count() == 36
    assert team.filter(counts=True).count() == 36
    assert team.filter(estimated=True).count() == 0
