import csv
import math
import os

import pytest

from racedbapp.shared import agegrade

MILE_M = 1609.344
MARATHON_M = 42195.0

# Published open-class standards (seconds) from the committed reference data.
OPEN_5K_M = 769.0  # 12:49
OPEN_8K_M = 1255.0  # 20:55
OPEN_10K_M = 1584.0  # 26:24
OPEN_MILE_M = 227.0  # 3:47
OPEN_800_M = 100.91  # World Athletics WR
# Published Alan Jones 2025 factor: 8 km, Male, age 50.
FACTOR_8K_M_50 = 0.885


def _factor(distance_m, gender, age):
    """Recover a committed factor through the public API (open / age-standard)."""
    return agegrade.standard_seconds(distance_m, gender, None) / agegrade.standard_seconds(
        distance_m, gender, age
    )


def _committed_road_opens(gender):
    """Committed road open standards as ``[(distance_m, open_seconds), ...]``.

    Read straight from the versioned CSV so interpolation tests compare the
    implementation against the committed ground truth, never against the
    implementation's own output.
    """
    path = os.path.join(agegrade.DATA_DIR, "road_open_standards.csv")
    with open(path, newline="") as fh:
        rows = [
            (float(row["distance_m"]), float(row["open_seconds"]))
            for row in csv.DictReader(fh)
            if row["gender"] == gender
        ]
    return sorted(rows)


# --------------------------------------------------------------------------- #
# AG% formula
# --------------------------------------------------------------------------- #
def test_age_grade_equals_100_at_standard():
    standard = agegrade.standard_seconds(5000, "M", 30)
    assert agegrade.age_grade(5000, "M", 30, standard) == pytest.approx(100.0)


def test_age_grade_above_100_when_faster_and_uncapped():
    standard = agegrade.standard_seconds(5000, "M", 30)
    grade = agegrade.age_grade(5000, "M", 30, standard / 2)
    assert grade > 100.0
    assert grade == pytest.approx(200.0)  # uncapped


def test_age_grade_is_50_at_double_time():
    standard = agegrade.standard_seconds(5000, "M", 30)
    assert agegrade.age_grade(5000, "M", 30, standard * 2) == pytest.approx(50.0)


# --------------------------------------------------------------------------- #
# Exact-match at committed anchors
# --------------------------------------------------------------------------- #
def test_exact_anchor_uses_published_factor():
    # age_standard = open_standard / published factor
    expected = OPEN_8K_M / FACTOR_8K_M_50
    assert agegrade.standard_seconds(8000, "M", 50) == pytest.approx(expected, abs=1e-6)


def test_open_standard_committed_per_distance():
    assert agegrade.standard_seconds(5000, "M", None) == pytest.approx(OPEN_5K_M)
    assert agegrade.standard_seconds(10000, "M", None) == pytest.approx(OPEN_10K_M)


# --------------------------------------------------------------------------- #
# Log-distance factor interpolation
# --------------------------------------------------------------------------- #
def test_log_distance_interpolation_reproduces_published_intermediate():
    # Reproduce the published 8K factor from the 5K and 10K anchors.
    f5 = _factor(5000, "M", 50)
    f10 = _factor(10000, "M", 50)
    published_8k = _factor(8000, "M", 50)

    u_log = math.log(8000 / 5000) / math.log(10000 / 5000)
    log_interp = f5 * (1 - u_log) + f10 * u_log

    u_lin = (8000 - 5000) / (10000 - 5000)
    lin_interp = f5 * (1 - u_lin) + f10 * u_lin

    assert abs(log_interp - published_8k) < 2e-4  # ~3e-5 in practice
    assert abs(lin_interp - published_8k) > 1e-4  # linear-distance is worse


# --------------------------------------------------------------------------- #
# Open-standard interpolation, validated against ground truth
#
# These tests never compare the implementation against its own formula. The
# ground truths are (a) the committed anchor standards themselves, (b) the
# physical shape of world-record performances (pace slows as distance grows),
# and (c) an independent calculator (runbundle.com) built on the same
# Alan Jones 2025 tables.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("gender", ["M", "F"])
def test_open_interpolation_reconstructs_committed_anchors(gender):
    # Leave-one-out: drop each sub-marathon interior anchor and predict its
    # committed open standard by linear-distance interpolation between its
    # neighbours. Worst case is ~1.2% (M marathon from 30 km and 50 km); the
    # log-distance weighting this replaced missed the M 5 km anchor by +8%.
    opens = _committed_road_opens(gender)
    for (d_lo, o_lo), (d_mid, o_mid), (d_hi, o_hi) in zip(opens, opens[1:], opens[2:]):
        if d_mid > MARATHON_M:
            break  # ultra anchors are too sparse for a meaningful bound
        v = (d_mid - d_lo) / (d_hi - d_lo)
        predicted = o_lo * (1 - v) + o_hi * v
        assert predicted == pytest.approx(o_mid, rel=0.015), (gender, d_mid)


@pytest.mark.parametrize("gender", ["M", "F"])
def test_open_standard_pace_never_speeds_up_with_distance(gender):
    # World-best pace per km only slows as the distance grows. The log-distance
    # bug violated this: it gave a 3 km open standard of 8:45 (2:55/km) versus
    # 2:34/km at 5 km. Sample every anchor and every inter-anchor midpoint.
    anchors = [d for d, _ in _committed_road_opens(gender)]
    samples = sorted(
        anchors + [math.sqrt(lo * hi) for lo, hi in zip(anchors, anchors[1:])]
    )
    paces = [agegrade.standard_seconds(d, gender, None) / d for d in samples]
    for (d, slower), (d_prev, faster) in zip(
        zip(samples[1:], paces[1:]), zip(samples, paces)
    ):
        assert slower >= faster * (1 - 1e-9), (gender, d_prev, d)


def test_3k_open_standard_matches_independent_calculator():
    # runbundle.com/tools/age-grading-calculator (same Alan Jones 2025 road
    # tables) reports a 7:29.3 (449.3 s) open-class standard for 3 km road,
    # consistent with the 7:20.67 track 3000 m world record. The log-distance
    # bug produced 8:44.8 here.
    assert agegrade.standard_seconds(3000, "M", None) == pytest.approx(449.3, abs=1.0)


def test_3k_age_grade_matches_independent_calculator():
    # Regression for the e-60 2026 series: M68 running 3 km in 11:50 scored
    # 99.37 under the log-distance bug. runbundle reports 85.35 for the same
    # inputs; we get ~85.1 (runbundle interpolates the age factor linearly,
    # we keep Jones' log-distance factor scheme — a ~0.3 point difference).
    grade = agegrade.age_grade(3000, "M", 68, 11 * 60 + 50)
    assert 84.0 < grade < 86.0


# --------------------------------------------------------------------------- #
# Road-vs-track resolution at the 1-mile floor
# --------------------------------------------------------------------------- #
def test_mile_floor_resolves_to_road():
    # At/above the floor, the road mile standard is used.
    assert agegrade.standard_seconds(MILE_M, "M", None) == pytest.approx(OPEN_MILE_M)


def test_below_mile_floor_resolves_to_track():
    # 1500 m and 800 m are below the floor: track standards apply.
    assert agegrade.standard_seconds(1500, "M", None) == pytest.approx(206.0)
    assert agegrade.standard_seconds(800, "M", None) == pytest.approx(OPEN_800_M)


# --------------------------------------------------------------------------- #
# Age handling: None, peak, and clamping
# --------------------------------------------------------------------------- #
def test_none_age_uses_open_standard():
    assert agegrade.standard_seconds(10000, "M", None) == pytest.approx(OPEN_10K_M)


def test_known_young_age_clamps_not_open():
    # A known 4-year-old clamps to the youngest road age (5), distinct from the
    # factor-1.0 open standard a None age would use.
    clamped = agegrade.standard_seconds(10000, "M", 4)
    assert clamped == pytest.approx(agegrade.standard_seconds(10000, "M", 5))
    assert clamped > agegrade.standard_seconds(10000, "M", None)


def test_old_age_clamps_to_oldest():
    assert agegrade.standard_seconds(10000, "M", 200) == pytest.approx(
        agegrade.standard_seconds(10000, "M", 99)
    )


def test_track_age_below_floor_clamps_to_20():
    # Below the track floor (age 20 = factor 1.0 = open standard).
    assert agegrade.standard_seconds(800, "M", 16) == pytest.approx(OPEN_800_M)
    assert agegrade.standard_seconds(800, "M", 16) == pytest.approx(
        agegrade.standard_seconds(800, "M", 20)
    )


# --------------------------------------------------------------------------- #
# Gender routing
# --------------------------------------------------------------------------- #
def test_male_and_female_use_their_tables():
    assert agegrade.standard_seconds(5000, "F", 30) != agegrade.standard_seconds(5000, "M", 30)


def test_blank_and_unknown_route_to_default_male():
    male = agegrade.standard_seconds(5000, "M", 30)
    assert agegrade.standard_seconds(5000, "", 30) == male
    assert agegrade.standard_seconds(5000, "X", 30) == male
    assert agegrade.standard_seconds(5000, None, 30) == male


def test_default_gender_table_override():
    female = agegrade.standard_seconds(5000, "F", 30)
    assert agegrade.standard_seconds(5000, "X", 30, default_gender_table="F") == female


# --------------------------------------------------------------------------- #
# Ultra distances within range
# --------------------------------------------------------------------------- #
def test_ultra_distances_within_range():
    assert agegrade.standard_seconds(50000, "M", None) == pytest.approx(8820.0)
    assert agegrade.standard_seconds(100000, "M", None) == pytest.approx(21360.0)
    assert agegrade.age_grade(50000, "M", 45, 9000.0) > 0


# --------------------------------------------------------------------------- #
# Out-of-range distances
# --------------------------------------------------------------------------- #
def test_below_track_floor_raises():
    with pytest.raises(ValueError, match="50"):
        agegrade.standard_seconds(50, "M", 30)


def test_above_largest_anchor_raises():
    with pytest.raises(ValueError, match="250000"):
        agegrade.standard_seconds(250000, "M", 30)


def test_gap_between_track_and_road_raises():
    # 1550 m: below the 1-mile road floor but above the 1500 m track anchor.
    with pytest.raises(ValueError):
        agegrade.standard_seconds(1550, "M", 30)
