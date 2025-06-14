from racedbapp.shared import types


def test_namedresult_fields():
    nr = types.namedresult(
        place=1,
        guntime="1:23:45",
        athlete="Alice",
        year=2024,
        category="F30-39",
        city="Springfield",
        age=32,
        race_slug="test-race",
        member=True,
    )
    assert nr.place == 1
    assert nr.athlete == "Alice"
    assert nr.race_slug == "test-race"
    assert nr.member is True


def test_namedteamrecord_fields():
    ntr = types.namedteamrecord(
        team_category_name="Open",
        team_category_slug="open",
        total_time="2:34:56",
        winning_team="TeamX",
        year=2024,
        avg_time="1:17:28",
        race_slug="test-race",
    )
    assert ntr.team_category_name == "Open"
    assert ntr.winning_team == "TeamX"
    assert ntr.avg_time == "1:17:28"


def test_choice_url_encoding():
    c = types.Choice("Test", "http://example.com/a b?x=1&y=2")
    assert c.name == "Test"
    # The full URL is encoded, including the scheme
    assert c.url == "http%3A//example.com/a+b?x=1&y=2"


def test_choice_comparison():
    c1 = types.Choice("A", "url1")
    c2 = types.Choice("B", "url2")
    assert c1 < c2
    assert c1 == types.Choice("A", "url1")
    assert c1 != c2


def test_filter_equality():
    c1 = types.Choice("A", "url1")
    c2 = types.Choice("B", "url2")
    f1 = types.Filter(current=c1, choices=[c1, c2])
    f2 = types.Filter(current=c1, choices=[c1, c2])
    f3 = types.Filter(current=c2, choices=[c1, c2])
    assert f1 == f2
    assert f1 != f3
