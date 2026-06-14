"""Pure-Python age-grade computation backed by versioned reference data.

Age grading compares a performance to the age- and sex-specific standard for its
distance: ``AG% = age_standard / actual × 100``. The age standard is derived from
the committed open-class standard and a per-age factor:
``age_standard = open_standard / factor`` (peak ages carry factor ``1.0``, so an
unknown age resolves straight to the open standard).

This module has **no Django imports** — the view layer converts model fields
(``Distance.km`` → metres, ``guntime`` → seconds, age cascade) and calls in here.
Reference data lives in ``agegrade_data/`` and is parsed once per process; see
``agegrade_data/README.md`` for provenance.

Distance resolution:
    * Road wins where a distance exists on both surfaces. The track tables apply
      only below the 1-mile (1609.344 m) road floor.
    * A distance matching a committed anchor uses that anchor's factor directly.
    * Otherwise the factor (and open standard) are interpolated between the two
      nearest anchors using **log-distance weighting** ``u = ln(d/d_lo) /
      ln(d_hi/d_lo)`` and ``age_standard = open_interp / factor_interp``.
    * A distance outside the committed-anchor span raises ``ValueError``.
"""

import csv
import functools
import math
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agegrade_data")

#: Gender table used for nonbinary / blank / unrecognized gender. Changing this
#: one constant moves the default for the whole codebase.
DEFAULT_GENDER_TABLE = "M"

#: Distances at or above the 1-mile road floor resolve to the road tables;
#: anything below it falls back to the track tables.
ROAD_FLOOR_M = 1609.344

#: A distance within this relative tolerance of a committed anchor is treated as
#: an exact match (so e.g. a mile stored as 1609 m still hits the mile anchor).
_REL_TOL = 1e-3


class _Surface:
    """Parsed reference data for one surface (road or track)."""

    def __init__(self, factor_path, open_path):
        self.open = {}  # (gender, distance_m) -> open_seconds
        self.factors = {}  # (gender, distance_m) -> {age: factor}
        self._age_bounds = {}  # (gender, distance_m) -> (min_age, max_age)
        self.distances = {"M": set(), "F": set()}  # gender -> {distance_m}

        with open(open_path, newline="") as fh:
            for row in csv.DictReader(fh):
                key = (row["gender"], float(row["distance_m"]))
                self.open[key] = float(row["open_seconds"])

        with open(factor_path, newline="") as fh:
            for row in csv.DictReader(fh):
                key = (row["gender"], float(row["distance_m"]))
                self.factors.setdefault(key, {})[int(row["age"])] = float(row["factor"])

        for key, ages in self.factors.items():
            self._age_bounds[key] = (min(ages), max(ages))
            self.distances[key[0]].add(key[1])

        # gender -> sorted list of anchor distances
        self.anchors = {g: sorted(d) for g, d in self.distances.items()}

    def factor_at(self, gender, distance_m, age):
        """Factor for an exact anchor distance, with the age clamped in range."""
        ages = self.factors[(gender, distance_m)]
        if age is None:
            return 1.0
        lo, hi = self._age_bounds[(gender, distance_m)]
        return ages[min(max(age, lo), hi)]


@functools.lru_cache(maxsize=None)
def _load():
    """Parse and cache the reference data (once per process)."""
    road = _Surface(
        os.path.join(DATA_DIR, "road_factors.csv"),
        os.path.join(DATA_DIR, "road_open_standards.csv"),
    )
    track = _Surface(
        os.path.join(DATA_DIR, "track_factors.csv"),
        os.path.join(DATA_DIR, "track_open_standards.csv"),
    )
    return {"road": road, "track": track}


def _resolve_gender(gender, default_gender_table):
    g = (gender or "").strip().upper()
    if g in ("M", "F"):
        return g
    return default_gender_table


def _match_anchor(anchors, distance_m):
    """Return the anchor within tolerance of ``distance_m``, else ``None``."""
    for anchor in anchors:
        if abs(distance_m - anchor) <= _REL_TOL * anchor:
            return anchor
    return None


def _bracket(anchors, distance_m):
    """Return the two anchors bracketing ``distance_m``."""
    for lo, hi in zip(anchors, anchors[1:]):
        if lo <= distance_m <= hi:
            return lo, hi
    raise ValueError(f"distance {distance_m:g} m has no bracketing anchors")


def standard_seconds(distance_m, gender, age, default_gender_table=DEFAULT_GENDER_TABLE):
    """Resolve the age-standard time (seconds) for a distance, gender, and age.

    ``age`` of ``None`` uses factor ``1.0`` (the open standard); a known age
    outside the table range is clamped to the nearest in-range age. Raises
    ``ValueError`` if ``distance_m`` is outside the committed-anchor span.
    """
    table_gender = _resolve_gender(gender, default_gender_table)
    data = _load()
    if distance_m >= ROAD_FLOOR_M * (1 - _REL_TOL):
        surface, surface_name = data["road"], "road"
    else:
        surface, surface_name = data["track"], "track"

    anchors = surface.anchors[table_gender]
    lo, hi = anchors[0], anchors[-1]
    if distance_m < lo * (1 - _REL_TOL) or distance_m > hi * (1 + _REL_TOL):
        raise ValueError(
            f"distance {distance_m:g} m is outside the committed {surface_name} "
            f"age-grade range ([{lo:g}, {hi:g}] m)"
        )

    anchor = _match_anchor(anchors, distance_m)
    if anchor is not None:
        factor = surface.factor_at(table_gender, anchor, age)
        open_seconds = surface.open[(table_gender, anchor)]
    else:
        d_lo, d_hi = _bracket(anchors, distance_m)
        u = math.log(distance_m / d_lo) / math.log(d_hi / d_lo)
        factor = (
            surface.factor_at(table_gender, d_lo, age) * (1 - u)
            + surface.factor_at(table_gender, d_hi, age) * u
        )
        open_seconds = (
            surface.open[(table_gender, d_lo)] * (1 - u) + surface.open[(table_gender, d_hi)] * u
        )
    return open_seconds / factor


def age_grade(distance_m, gender, age, actual_seconds, default_gender_table=DEFAULT_GENDER_TABLE):
    """Return ``standard_seconds / actual_seconds × 100`` — uncapped, unrounded."""
    standard = standard_seconds(distance_m, gender, age, default_gender_table)
    return standard / actual_seconds * 100
