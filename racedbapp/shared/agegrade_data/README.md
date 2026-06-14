# Age-grade reference data

Versioned reference data backing `racedbapp/shared/agegrade.py`. These committed
CSV files are the **runtime source of truth**; `generate.py` reproduces them
from their public sources but is never imported at runtime.

## Files

| File | Columns | Contents |
| --- | --- | --- |
| `road_factors.csv` | `gender,distance_m,age,factor` | Alan Jones 2025 road per-age factors (ages 5–99) for 22 anchors, 1 mile → 200 km / 100 mi. |
| `road_open_standards.csv` | `gender,distance_m,open_seconds` | Open-class (peak) standard time per road `(gender, distance)`. |
| `track_factors.csv` | `gender,distance_m,age,factor` | WMA 2023 one-year factors for 100m/200m/400m/800m/1000m/1500m (ages 20–110; 20–29 = 1.0). |
| `track_open_standards.csv` | `gender,distance_m,open_seconds` | World Athletics outdoor WR open standard per track `(gender, distance)`. |
| `manifest.json` | — | Version, generation date, and pinned source provenance. |

The data is stored in the published **open-standard + per-age-factor** shape, not
as pre-resolved age-standard times. The age standard is derived at runtime as
`age_standard = open_standard / factor`, and the age grade is
`AG% = age_standard / actual × 100`. Peak ages carry factor `1.0`, so an unknown
age (factor `1.0`) resolves to the committed open standard with no sentinel row.

## Shape & conventions

- `distance_m` is the canonical distance in metres at full precision (e.g. the
  mile is `1609.344`, the marathon is `42195`). Mile-based road anchors use the
  exact `1609.344 m` mile.
- Factors are four decimal places, matching the published tables.
- Road wins where a distance exists on both surfaces; the track tables apply
  only **below the 1-mile (1609.344 m) road floor**.
- Non-anchor distances are resolved by **log-distance interpolation of the
  factor** between the two nearest anchors — Alan Jones' verified 2025 scheme,
  which reproduces his published per-distance tables to ≈0.00005 (vs ≈0.0008 for
  linear-distance interpolation).

## Sources

- **Road (Alan Jones 2025, CC0):**
  <https://github.com/AlanLyttonJones/Age-Grade-Tables> — `2025 Files/AgeGrade.zip`.
  Public-domain release approved 2025-01-10 by USATF MLDR. The per-distance
  `AgeGrade.<dist>` files carry the open-class M/F standard on their first two
  lines followed by `<gender> <age> <factor>` rows. The marathon anchor is taken
  from `AgeGrade.42k` (42.195 km); the duplicate `AgeGrade.26m` is skipped.
- **Track factors (WMA 2023 Appendix B):**
  <https://world-masters-athletics.org/wp-content/uploads/2023/02/2023-WMA-Appendix-B.pdf> —
  the "ONE-YEAR AGE FACTORS" running tables (men & women), columns 100m–1500m,
  ages 30–110. Ages 20–29 are set to factor `1.0` and the table is floored at
  age 20 (younger known ages clamp to 20), so no age-group-world-record source
  is needed for the track side.
- **Track open standards (World Athletics outdoor WRs):** the standard outdoor
  world record where a "short track" variant also exists. Retrieved 2026-06-13:
  100m 9.58/10.49, 200m 19.19/21.34, 400m 43.03/47.60, 800m 100.91/113.28,
  1000m 131.96/148.98, 1500m 206.00/228.68 (M/F, seconds).

## Regeneration

```bash
# Road needs only the standard library; track extraction needs pdfplumber.
pip install pdfplumber
python racedbapp/shared/agegrade_data/generate.py --manifest-date $(date +%F)
```

`generate.py` downloads both sources (pass `--road-zip` / `--wma-pdf` to use
local copies), reshapes them into the CSVs above, and rewrites `manifest.json`.
Bump `version` in `generate.py` when the upstream tables change.
