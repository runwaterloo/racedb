import types
from unittest import mock

# Import the functions directly from the command module
from racedbapp.management.commands.addraces import (
    get_extra_dict,
    get_member,
    get_results_from_google,
)


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
