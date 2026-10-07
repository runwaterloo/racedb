import csv
import io

from racedbapp.art_parse import main, str2dt

HEADINGS = [
    "Race Distance (in meters)",
    "Bib #",
    "Overall Place",
    "Finishing Time",
    "First Name",
    "Last Name",
    "Sex",
    "Eligible Division(s)",
    "Age",
    "Chip Time",
    "City",
    "Split Times",
]


def race_csv(athletes, split_heading="Split Times"):
    headings = [
        split_heading if heading == "Split Times" else heading
        for heading in HEADINGS
    ]
    rows = [headings]
    for bib, place, first_name, last_name, guntime, splits in athletes:
        for split in splits:
            rows.append([
                "5000",
                bib,
                str(place),
                guntime,
                first_name,
                last_name,
                "X",
                "Open",
                "30",
                guntime,
                "City",
                split,
            ])
    content = io.StringIO()
    csv.writer(content).writerows(rows)
    return content.getvalue()


def split_seconds(result):
    return [
        getattr(result, f"split{lap}").total_seconds()
        for lap in range(1, 5)
    ]


def test_split_formats_and_single_lap(monkeypatch):
    content = race_csv([
        (
            "1",
            1,
            "Per",
            "Lap",
            "00:19:31",
            ["00:05:06", "00:04:29", "00:05:31", "00:04:25"],
        ),
        (
            "2",
            2,
            "Cumulative",
            "Athlete",
            "00:19:31",
            ["00:05:06", "00:09:35", "00:15:06", "00:19:31"],
        ),
        (
            "3",
            3,
            "Single",
            "Athlete",
            "00:05:06",
            ["00:05:06"],
        ),
    ])
    original_open = open
    monkeypatch.setattr(
        "builtins.open",
        lambda path, *args, **kwargs: io.StringIO(content)
        if path == "/tmp/art.csv"
        else original_open(path, *args, **kwargs),
    )

    results, logs = main("5000")

    assert split_seconds(results[0]) == [306, 269, 331, 265]
    assert split_seconds(results[1]) == [306, 269, 331, 265]
    assert not hasattr(results[2], "split1")
    assert not logs


def test_cumulative_split_accepts_two_second_guntime_difference(monkeypatch):
    content = race_csv([
        (
            "1",
            1,
            "Rounded",
            "Gun",
            "00:19:31",
            ["00:05:06", "00:09:35", "00:15:06", "00:19:33"],
        ),
    ])
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(content),
    )

    results, logs = main("5000")

    assert split_seconds(results[0]) == [306, 269, 331, 267]
    assert not logs


def test_ambiguous_splits_are_kept_and_logged(monkeypatch):
    content = race_csv([
        (
            "42",
            1,
            "Ambiguous",
            "Runner",
            "00:20:00",
            ["00:05:06", "00:04:29", "00:05:31", "00:04:25"],
        ),
    ])
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(content),
    )

    results, logs = main("5000")

    assert split_seconds(results[0]) == [306, 269, 331, 265]
    assert "WARNING: Splits for Ambiguous Runner (bib 42)" in logs
    assert "using raw values" in logs


def test_chip_time_split_heading_is_supported(monkeypatch):
    content = race_csv([
        (
            "7",
            1,
            "Chip",
            "Runner",
            "00:10:00",
            ["00:05:00", "00:05:00"],
        ),
    ], split_heading="Split Times (by chip time)")
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(content),
    )

    results, logs = main("5000")

    assert [
        getattr(results[0], "split1").total_seconds(),
        getattr(results[0], "split2").total_seconds(),
    ] == [300, 300]
    assert not logs


def test_result_attribute_order_is_preserved(monkeypatch):
    content = race_csv([
        (
            "1",
            1,
            "Ordered",
            "Runner",
            "00:10:00",
            ["00:05:00", "00:05:00"],
        ),
    ])
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(content),
    )

    results, _ = main("5000")

    assert list(vars(results[0])) == [
        "place",
        "bib",
        "athlete",
        "guntime",
        "gender",
        "age",
        "category",
        "chiptime",
        "city",
        "split1",
        "split2",
    ]


def test_trailing_empty_split_row_does_not_warn(monkeypatch):
    content = race_csv([
        (
            "1",
            1,
            "Trailing",
            "Blank",
            "00:10:00",
            ["00:05:00", "00:10:00", ""],
        ),
    ])
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(content),
    )

    results, logs = main("5000")

    assert [
        getattr(results[0], "split1").total_seconds(),
        getattr(results[0], "split2").total_seconds(),
    ] == [300, 300]
    assert not logs


def test_str2dt_accepts_durations_over_24_hours():
    assert str2dt("0098:35:36") == str2dt("98:35:36")
    assert str2dt("0098:35:36") is not False
