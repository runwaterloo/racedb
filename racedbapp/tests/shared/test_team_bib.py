"""Unit tests for bib-driven team scoring (no DB)."""

from racedbapp.shared.team_bib import assign_counts_and_order, compute_team_places


def _runner(place, guntime_seconds, bib=None):
    runner = {"place": place, "guntime_seconds": guntime_seconds}
    if bib is not None:
        runner["bib"] = bib
    return runner


class TestAssignCountsAndOrder:
    def test_top_n_count_others_do_not(self):
        runners = [
            _runner(10, 3000),
            _runner(1, 2100),
            _runner(5, 2500),
            _runner(3, 2300),
        ]
        result = assign_counts_and_order(runners, counts=3)
        assert [r["place"] for r in result] == [1, 3, 5, 10]
        assert [r["counts"] for r in result] == [True, True, True, False]

    def test_counts_zero_marks_all_false(self):
        runners = [_runner(1, 2100), _runner(2, 2200)]
        result = assign_counts_and_order(runners, counts=0)
        assert all(r["counts"] is False for r in result)

    def test_counts_larger_than_team_counts_all_true(self):
        runners = [_runner(2, 2200), _runner(1, 2100)]
        result = assign_counts_and_order(runners, counts=5)
        assert all(r["counts"] is True for r in result)

    def test_all_runners_receive_counts_key(self):
        runners = [_runner(2, 2200), _runner(1, 2100)]
        result = assign_counts_and_order(runners, counts=1)
        assert result[0]["counts"] is True
        assert result[1]["counts"] is False


class TestComputeTeamPlaces:
    def _team(self, name, runners):
        return {
            "team_name": name,
            "counting_runners": runners,
            "guntime_total": sum(r["guntime_seconds"] for r in runners),
        }

    def test_ranked_by_guntime_sum(self):
        teams = [
            self._team("Slow", [_runner(1, 3000), _runner(2, 3100)]),
            self._team("Fast", [_runner(5, 2100), _runner(9, 2200)]),
        ]
        assert compute_team_places(teams) == [2, 1]

    def test_tie_broken_by_last_counting_runner_place(self):
        # Both teams total 4400s; Fast's last counter has better place.
        teams = [
            self._team(
                "Team A",
                [_runner(1, 2100), _runner(20, 2300)],  # last place 20
            ),
            self._team(
                "Team B",
                [_runner(2, 2200), _runner(3, 2200)],  # last place 3
            ),
        ]
        assert compute_team_places(teams) == [2, 1]

    def test_places_are_contiguous(self):
        teams = [
            self._team("C", [_runner(7, 3400)]),
            self._team("A", [_runner(1, 2100)]),
            self._team("B", [_runner(3, 2500)]),
        ]
        assert compute_team_places(teams) == [3, 1, 2]

    def test_does_not_mutate_input(self):
        teams = [
            self._team("A", [_runner(1, 2100)]),
            self._team("B", [_runner(2, 2200)]),
        ]
        result = compute_team_places(teams)
        assert result == [1, 2]
        assert teams[0]["team_name"] == "A"  # order unchanged
