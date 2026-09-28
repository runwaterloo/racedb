import datetime
import types
from unittest import mock

from django.core.management import call_command

# Import the functions directly from the command module
from racedbapp.management.commands.addraces import (
    get_extra_dict,
    get_member,
    get_results_from_google,
    process_rwpbs,
)
from racedbapp.membership import update_membership
from racedbapp.models import Result


def test_addraces_add_results_from_fake_google_sheet(db, create_event):
    event = create_event()
    event.resultsurl = "https://docs.google.com/spreadsheets/d/fake_sheet_id/edit"
    event.save()
    fake_results = {
        "individual": [
            {
                "place": 1,
                "bib": "123",
                "athlete": "Fake Person",
                "guntime": "0:20:00",
                "gender": "F",
                "age": 25,
                "category": "F25-29",
                "chiptime": "0:19:19",
                "city": "Anytown",
            }
        ],
        "team": [],
    }
    with (
        mock.patch(
            "racedbapp.management.commands.addraces.get_results_from_google",
            return_value=fake_results,
        ),
        mock.patch("racedbapp.management.commands.addraces.tasks.clear_cache.delay"),
    ):
        # ...rest of your test...
        call_command("addraces", event_id=event.id)
    result = Result.objects.filter(event=event).first()
    assert result is not None
    assert result.athlete == "Fake Person"
    assert result.place == 1
    assert result.bib == "123"
    assert result.city == "Anytown"
    assert result.gender == "F"


def test_get_member_logic():
    # Mock event and membership objects
    event = types.SimpleNamespace(id=1)
    result = {"athlete": "Alice", "place": 5}
    membership = types.SimpleNamespace(
        names={"alice": "MEMBER1"},
        includes={"1-5": "MEMBER2"},
        excludes={"1-5": ["MEMBER2"]},
    )
    # Should return MEMBER1 (from names)
    assert get_member(event, {"athlete": "Alice", "place": 6}, membership) == "MEMBER1"
    # Should return MEMBER2 (from includes)
    assert get_member(event, result, membership) is None  # Excluded
    # Not found
    assert get_member(event, {"athlete": "Bob", "place": 1}, membership) is None


def test_process_rwpbs_same_day_events_preserves_prior_pb(
    create_distance,
    create_race,
    create_event,
    create_category,
    create_rwmember,
    create_result,
    create_sequel,
):
    distance = create_distance(km=5)
    race = create_race()
    event_date = datetime.date(2026, 1, 1)
    first_event = create_event(date=event_date, race=race, distance=distance)
    second_event = create_event(
        date=event_date,
        race=race,
        distance=distance,
        sequel=create_sequel(),
        name_suffix="second",
    )
    category = create_category()
    slower_member = create_rwmember(name_suffix="slower")
    faster_member = create_rwmember(name_suffix="faster")

    slower_first = create_result(
        event=first_event,
        category=category,
        athlete=slower_member.name,
        rwmember=slower_member,
        guntime=datetime.timedelta(minutes=25),
    )
    faster_first = create_result(
        event=first_event,
        category=category,
        athlete=faster_member.name,
        rwmember=faster_member,
        place=2,
        guntime=datetime.timedelta(minutes=25),
    )
    process_rwpbs(first_event)
    slower_first.refresh_from_db()
    faster_first.refresh_from_db()
    assert slower_first.isrwpb is True
    assert faster_first.isrwpb is True

    slower_second = create_result(
        event=second_event,
        category=category,
        athlete=slower_member.name,
        rwmember=slower_member,
        guntime=datetime.timedelta(minutes=26),
    )
    faster_second = create_result(
        event=second_event,
        category=category,
        athlete=faster_member.name,
        rwmember=faster_member,
        place=2,
        guntime=datetime.timedelta(minutes=24),
    )

    process_rwpbs(second_event)

    slower_first.refresh_from_db()
    faster_first.refresh_from_db()
    slower_second.refresh_from_db()
    faster_second.refresh_from_db()
    assert slower_first.isrwpb is True
    assert faster_first.isrwpb is True
    assert slower_second.isrwpb is False
    assert faster_second.isrwpb is True

    update_membership(slower_member)
    update_membership(faster_member)
    slower_first.refresh_from_db()
    faster_first.refresh_from_db()
    slower_second.refresh_from_db()
    faster_second.refresh_from_db()
    assert slower_first.isrwpb is True
    assert faster_first.isrwpb is True
    assert slower_second.isrwpb is False
    assert faster_second.isrwpb is True


def test_get_results_from_google():
    # Patch gspread and worksheet methods
    with mock.patch("racedbapp.management.commands.addraces.gspread") as mock_gspread:
        mock_gc = mock.Mock()
        mock_sh = mock.Mock()
        mock_ws_ind = mock.Mock()
        mock_ws_team = mock.Mock()
        mock_ws_ind.get_all_records.return_value = [{"a": 1}]
        mock_ws_team.get_all_records.return_value = [{"b": 2}]
        mock_sh.worksheet.side_effect = (
            lambda name: mock_ws_ind if name == "individual" else mock_ws_team
        )
        mock_sh.worksheets.return_value = [
            types.SimpleNamespace(title="individual"),
            types.SimpleNamespace(title="team"),
        ]
        mock_gc.open_by_url.return_value = mock_sh
        mock_gspread.service_account.return_value = mock_gc
        results = get_results_from_google("http://fake-url")
        assert results["individual"] == [{"a": 1}]
        assert results["team"] == [{"b": 2}]


def test_get_extra_dict():
    result = {
        "division": "M40-49",
        "relay_team": "TeamX",
        "Hill Time": "0:05:00",
        "split1": "0:10:00",
        "split2": "0:20:00",
        "other": 123,
    }
    extra = get_extra_dict(result)
    assert extra["division"] == "M40-49"
    assert extra["relay_team"] == "TeamX"
    assert extra["Hill Time"] == "0:05:00"
    assert extra["split1"] == "0:10:00"
    assert extra["split2"] == "0:20:00"
    assert "other" not in extra
