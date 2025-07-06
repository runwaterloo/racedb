from racedbapp.shared import endurrun


def test_get_member_endurrace():
    class MockResult:
        def __init__(self, athlete):
            self.athlete = athlete.lower()

    class MockMembership:
        def __init__(self, names):
            self.names = names

    membership = MockMembership(names={"alice": True, "bob": False})
    result1 = MockResult(athlete="Alice")
    result2 = MockResult(athlete="Bob")

    assert endurrun.get_member_endurrace(result1, membership) is True
    assert endurrun.get_member_endurrace(result2, membership) is False
