#!/usr/bin/env python3
"""Regenerate the committed age-grade reference data.

This script is **not** imported at runtime. The committed CSV files in this
directory are the runtime source of truth; this script documents and reproduces
them from their public-domain / published sources.

Two data sets are produced:

Road (Alan Jones 2025, CC0)
    Downloads the ``AgeGrade.zip`` bundle of per-distance factor tables from
    Alan Jones' public-domain 2025 release and reshapes each ``AgeGrade.<dist>``
    file into the committed ``road_factors.csv`` (gender,distance_m,age,factor)
    and ``road_open_standards.csv`` (gender,distance_m,open_seconds). Each
    source file stores the open-class M/F standard on its first two lines,
    followed by ``<gender> <age> <factor>`` rows (ages 5-99).

Track (WMA 2023 Appendix B + World Athletics WRs)
    Extracts the "ONE-YEAR AGE FACTORS" running tables (ages 30-110) for
    100m/200m/400m/800m/1000m/1500m from the 2023 WMA Rulebook Appendix B PDF,
    sets ages 20-29 to factor 1.0 (the table is floored at age 20), and pairs
    them with the World Athletics outdoor world-record open standards below.
    Produces ``track_factors.csv`` and ``track_open_standards.csv`` in the same
    shape as the road files.

Requirements:
    * Road: standard library only (urllib, zipfile).
    * Track: ``pdfplumber`` (dev-only; ``pip install pdfplumber``) for
      coordinate-based table extraction, which is the only reliable way to read
      the wide numeric tables (plain ``pdftotext`` misaligns the tail ages).

Regeneration:
    python racedbapp/shared/agegrade_data/generate.py

Use ``--manifest-date YYYY-MM-DD`` to stamp ``manifest.json`` deterministically.

Sources:
    Road:  https://github.com/AlanLyttonJones/Age-Grade-Tables
           (2025 Files/AgeGrade.zip)
    Track: https://world-masters-athletics.org/wp-content/uploads/2023/02/2023-WMA-Appendix-B.pdf
           World Athletics outdoor world records (open standards).
"""

import argparse
import csv
import io
import json
import os
import urllib.request
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

ROAD_ZIP_URL = (
    "https://raw.githubusercontent.com/AlanLyttonJones/Age-Grade-Tables/"
    "master/2025%20Files/AgeGrade.zip"
)
WMA_PDF_URL = (
    "https://world-masters-athletics.org/wp-content/uploads/2023/02/2023-WMA-Appendix-B.pdf"
)
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

MILE_M = 1609.344

# Alan Jones AgeGrade.<suffix> filename -> committed distance in metres.
# The marathon is taken from "42k" (42.195 km); the duplicate "26m" file
# (same standards) is intentionally skipped to avoid a redundant anchor.
ROAD_DISTANCES = {
    "1mi": MILE_M,
    "4mi": 4 * MILE_M,
    "5k": 5000.0,
    "5mi": 5 * MILE_M,
    "6k": 6000.0,
    "7mi": 7 * MILE_M,
    "8k": 8000.0,
    "10k": 10000.0,
    "10mi": 10 * MILE_M,
    "12k": 12000.0,
    "15k": 15000.0,
    "20k": 20000.0,
    "hm": 21097.5,
    "25k": 25000.0,
    "30k": 30000.0,
    "42k": 42195.0,  # Marathon
    "50k": 50000.0,
    "50mi": 50 * MILE_M,
    "100k": 100000.0,
    "100mi": 100 * MILE_M,
    "150k": 150000.0,
    "200k": 200000.0,
}

# WMA one-year table running columns -> committed distance in metres.
TRACK_DISTANCES = {
    "100m": 100.0,
    "200m": 200.0,
    "400m": 400.0,
    "800m": 800.0,
    "1000m": 1000.0,
    "1500m": 1500.0,
}

# World Athletics outdoor world-record open standards, in seconds (M, F).
# Standard outdoor record where a "short track" variant also exists.
TRACK_OPEN_SECONDS = {
    "100m": {"M": 9.58, "F": 10.49},
    "200m": {"M": 19.19, "F": 21.34},
    "400m": {"M": 43.03, "F": 47.60},
    "800m": {"M": 100.91, "F": 113.28},
    "1000m": {"M": 131.96, "F": 148.98},
    "1500m": {"M": 206.00, "F": 228.68},
}

# WMA factors are published from age 30; the table is floored at age 20 and
# ages 20-29 are peak (factor 1.0).
TRACK_MIN_AGE = 20
TRACK_PEAK_MAX_AGE = 29


def _fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _parse_clock(text):
    """Parse an ``H:MM:SS`` (or ``HH:MM:SS``) clock string into float seconds."""
    parts = [int(p) for p in text.strip().split(":")]
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return float(seconds)


# --------------------------------------------------------------------------- #
# Road (Alan Jones 2025)
# --------------------------------------------------------------------------- #
def build_road(source_zip=None):
    """Return (factor_rows, open_rows) parsed from the Alan Jones 2025 bundle."""
    if source_zip and os.path.exists(source_zip):
        with open(source_zip, "rb") as fh:
            raw = fh.read()
    else:
        raw = _fetch(ROAD_ZIP_URL)

    factor_rows = []
    open_rows = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = {os.path.basename(n).split(".", 1)[-1]: n for n in zf.namelist()}
        for suffix, distance_m in sorted(ROAD_DISTANCES.items(), key=lambda kv: kv[1]):
            member = names.get(suffix)
            if member is None:
                raise SystemExit(f"AgeGrade.{suffix} not found in bundle")
            lines = zf.read(member).decode("utf-8").splitlines()
            for line in lines:
                parts = line.split()
                if not parts:
                    continue
                gender = parts[0]
                if ":" in parts[1]:  # open-standard header line, e.g. "M 0:12:49"
                    open_rows.append((gender, distance_m, _parse_clock(parts[1])))
                else:  # "<gender> <age> <factor>"
                    age = int(parts[1])
                    factor = float(parts[2])
                    factor_rows.append((gender, distance_m, age, factor))
    return factor_rows, open_rows


# --------------------------------------------------------------------------- #
# Track (WMA 2023 Appendix B)
# --------------------------------------------------------------------------- #
def _pdf_rows(page):
    """Cluster a page's words into rows (sorted left-to-right) by their y-top."""
    rows = defaultdict(list)
    for word in page.extract_words():
        rows[round(word["top"])].append((word["x0"], word["text"]))
    return [[text for _, text in sorted(cells)] for _, cells in sorted(rows.items())]


def build_track(source_pdf=None):
    """Return (factor_rows, open_rows) for the track distances.

    Extracts the WMA one-year running factors and pairs them with the World
    Athletics open standards. Ages 20-29 are set to factor 1.0.
    """
    import pdfplumber  # dev-only dependency

    if source_pdf and os.path.exists(source_pdf):
        pdf_bytes = open(source_pdf, "rb").read()
    else:
        pdf_bytes = _fetch(WMA_PDF_URL, headers={"User-Agent": BROWSER_UA})

    # gender -> {wma_col_label -> {age -> factor}}
    factors = {"M": defaultdict(dict), "F": defaultdict(dict)}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "ONE-YEAR AGE FACTORS" not in text:
                continue
            if "WOMEN" in text:
                gender = "F"
            elif "MEN" in text:
                gender = "M"
            else:
                continue
            header = None
            for cells in _pdf_rows(page):
                if not cells:
                    continue
                if cells[0] == "Age":
                    header = cells[1:]
                    continue
                if header is None or not cells[0].isdigit() or len(cells[0]) > 3:
                    continue
                if "100m" not in header:  # field-event page; skip
                    continue
                age = int(cells[0])
                values = cells[1:]
                if len(values) != len(header):
                    raise SystemExit(f"row width mismatch at age {age} ({gender})")
                for label, value in zip(header, values):
                    if label in TRACK_DISTANCES:
                        factors[gender][label][age] = float(value)

    factor_rows = []
    open_rows = []
    for label, distance_m in sorted(TRACK_DISTANCES.items(), key=lambda kv: kv[1]):
        for gender in ("M", "F"):
            open_rows.append((gender, distance_m, TRACK_OPEN_SECONDS[label][gender]))
            published = factors[gender].get(label)
            if not published:
                raise SystemExit(f"no WMA factors extracted for {label} ({gender})")
            min_pub = min(published)
            max_pub = max(published)
            for age in range(TRACK_MIN_AGE, max_pub + 1):
                if age <= TRACK_PEAK_MAX_AGE or age < min_pub:
                    factor = 1.0
                else:
                    factor = published[age]
                factor_rows.append((gender, distance_m, age, factor))
    return factor_rows, open_rows


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #
def _write_factor_csv(path, rows):
    rows = sorted(rows, key=lambda r: (r[0], r[1], r[2]))
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gender", "distance_m", "age", "factor"])
        for gender, distance_m, age, factor in rows:
            writer.writerow([gender, _fmt_distance(distance_m), age, f"{factor:.4f}"])


def _write_open_csv(path, rows):
    rows = sorted(rows, key=lambda r: (r[0], r[1]))
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["gender", "distance_m", "open_seconds"])
        for gender, distance_m, open_seconds in rows:
            writer.writerow([gender, _fmt_distance(distance_m), f"{open_seconds:g}"])


def _fmt_distance(distance_m):
    # Integer metres render without a trailing ".0"; fractional metres (miles)
    # keep their exact value at full precision.
    if float(distance_m).is_integer():
        return str(int(distance_m))
    return f"{distance_m:.6f}".rstrip("0").rstrip(".")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--road-zip", help="local AgeGrade.zip (else download)")
    parser.add_argument("--wma-pdf", help="local WMA Appendix B PDF (else download)")
    parser.add_argument("--manifest-date", help="YYYY-MM-DD stamp for manifest.json")
    args = parser.parse_args()

    road_factors, road_open = build_road(args.road_zip)
    _write_factor_csv(os.path.join(HERE, "road_factors.csv"), road_factors)
    _write_open_csv(os.path.join(HERE, "road_open_standards.csv"), road_open)
    print(f"road: {len(road_factors)} factor rows, {len(road_open)} open standards")

    track_factors, track_open = build_track(args.wma_pdf)
    _write_factor_csv(os.path.join(HERE, "track_factors.csv"), track_factors)
    _write_open_csv(os.path.join(HERE, "track_open_standards.csv"), track_open)
    print(f"track: {len(track_factors)} factor rows, {len(track_open)} open standards")

    manifest = {
        "version": "2025.1",
        "generated_on": args.manifest_date or "unset",
        "sources": [
            {
                "name": "Alan Jones Road Age-Grade Tables (2025)",
                "surface": "road",
                "url": "https://github.com/AlanLyttonJones/Age-Grade-Tables",
                "file": "2025 Files/AgeGrade.zip",
                "license": "CC0 / public domain",
                "approved": "2025-01-10 (USATF MLDR)",
                "notes": "Per-distance factor tables (ages 5-99) + open-class "
                "M/F standards. Marathon taken from AgeGrade.42k (42.195 km).",
            },
            {
                "name": "WMA 2023 Rulebook Appendix B one-year age factors",
                "surface": "track",
                "url": WMA_PDF_URL,
                "notes": "One-year running age factors for 100m-1500m, ages "
                "30-110; ages 20-29 set to factor 1.0 and the table is floored "
                "at age 20.",
            },
            {
                "name": "World Athletics outdoor world records (open standards)",
                "surface": "track",
                "url": "https://worldathletics.org/records/by-category/world-records",
                "retrieved": "2026-06-13",
                "notes": "Standard outdoor record used where a short-track variant also exists.",
            },
        ],
        "notes": "Committed CSVs are the runtime source of truth; this manifest "
        "is bumped on regeneration. Road wins where a distance exists in both "
        "surfaces; track applies below the 1-mile (1609.344 m) road floor.",
    }
    with open(os.path.join(HERE, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print("manifest.json written")


if __name__ == "__main__":
    main()
