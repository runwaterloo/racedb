"""Bib-driven team results: scoring and placement.

Pure functions only -- no Django models here, so this module can be
unit-tested without a database. The sheet-facing validation lives in
addraces.py; this module takes already-validated data.

Terminology:
- "runners" are a team's members joined (by bib) to individual results.
- "counting runners" are the top N by overall individual place, where
  N is the Teamcategory's counts value.
- Team places rank by the sum of guntimes of counting runners (lowest
  wins). Ties are broken by the overall individual place of each
  team's LAST counting runner (lower place wins). Individual places
  are unique, so this always resolves.
"""

from typing import Dict, List


def assign_counts_and_order(runners: List[Dict], counts: int) -> List[Dict]:
    """Return runners sorted by place, with counts set for the top N.

    Each runner is a dict with a "place" key (int) plus anything the
    caller wants preserved. The returned list is ordered by ascending
    place (this is also the athlete_team_place order). Runner dicts
    gain a "counts" key (bool): True for the top `counts` runners.
    """
    ordered = sorted(runners, key=lambda r: r["place"])
    for i, runner in enumerate(ordered):
        runner["counts"] = i < counts
    return ordered


def compute_team_places(teams: List[Dict]) -> List[int]:
    """Return the team_place for each team (index-aligned with input).

    Each team is a dict with:
    - "counting_runners": the team's runners already trimmed to its
      counting set, sorted by place, each with "place" (overall
      individual place, unique across all runners) and
      "guntime_seconds" (int).
    - "guntime_total": the sum of counting runners' guntimes.

    Teams with fewer counting runners than their category's counts must
    be skipped by the caller before calling this.

    Teams rank by guntime_total ascending; ties are broken by the
    overall place of each team's LAST counting runner (numerically
    lower place wins). Returns places 1..n contiguously.
    """

    def sort_key(team):
        return (
            team["guntime_total"],
            max(r["place"] for r in team["counting_runners"]),
        )

    ranked = sorted(teams, key=sort_key)
    places = {id(team): place for place, team in enumerate(ranked, start=1)}
    return [places[id(team)] for team in teams]
