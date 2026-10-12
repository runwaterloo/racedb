import csv
from datetime import timedelta


def main(art_distance, csv_path="/tmp/art.csv"):
    logs = ""
    results_dict = {}
    results = []
    with open(csv_path, newline='') as csvfile:
        rows = list(csv.reader(csvfile, delimiter=',', quotechar='"'))
    headings = rows[0]
    for i, row in enumerate(rows[1:]):
        distance = row[headings.index("Race Distance (in meters)")].strip()
        if distance != art_distance:  # skip other events
            continue
        bib = row[headings.index("Bib #")]
        try:
            place = int(row[headings.index("Overall Place")].strip())
        except Exception:
            logs += f"\nWARNING: Unable to find place in row {i+2}, skipping"
            continue
        guntime = row[headings.index("Finishing Time")].strip()
        if not guntime:
            logs += f"\nWARNING: No Finishing Time in row {i+2}, skipping"
            continue
        if "Split Times" in headings:
            split_heading = "Split Times"
        elif "Split Times (by chip time)" in headings:
            split_heading = "Split Times (by chip time)"
        else:
            raise ValueError("ERROR: Can't find valid Split Times column")
        if bib not in results_dict:
            results_dict[bib] = Result(place)
            results_dict[bib].bib = bib
            first_name = row[headings.index("First Name")].strip()
            last_name = row[headings.index("Last Name")].strip()
            results_dict[bib].athlete = f"{first_name} {last_name}"
            results_dict[bib].guntime = guntime
            results_dict[bib].gender = row[headings.index("Sex")].strip()
            categories = row[headings.index("Eligible Division(s)")].split("&")
            results_dict[bib].age = row[headings.index("Age")].strip()
            results_dict[bib].category = categories[-1].strip()
            results_dict[bib].chiptime = row[headings.index(
                "Chip Time")].strip()
            results_dict[bib].city = row[headings.index("City")].strip()
            results_dict[bib].laps = 0
        if row[headings.index(split_heading)]:
            results_dict[bib].laps += 1
            raw_split_time = row[headings.index(
                split_heading)].split()[-1].strip()
            split_time = str2dt(raw_split_time)
            if split_time:
                setattr(
                    results_dict[bib], f"raw_split{results_dict[bib].laps}", split_time)
            else:
                logs += f"\nWARNING: Unable to process split in row {i+2}, skipping"

    for k, v in results_dict.items():
        raw_splits = [
            getattr(v, f"raw_split{lap}", None)
            for lap in range(1, v.laps + 1)
        ]
        has_raw_splits = any(
            split_time is not None for split_time in raw_splits)
        complete_splits = all(
            split_time is not None for split_time in raw_splits)
        guntime = str2dt(v.guntime)
        tolerance = timedelta(seconds=2)
        cumulative = (
            complete_splits
            and len(raw_splits) > 1
            and all(raw_splits[index] < raw_splits[index + 1]
                    for index in range(len(raw_splits) - 1))
            and guntime
            and abs(raw_splits[-1] - guntime) <= tolerance
        )
        per_lap = (
            complete_splits
            and guntime
            and abs(sum(raw_splits, timedelta()) - guntime) <= tolerance
        )
        if cumulative:
            split_times = [
                raw_splits[0],
                *[raw_splits[index] - raw_splits[index - 1]
                  for index in range(1, len(raw_splits))],
            ]
        else:
            split_times = raw_splits
            if has_raw_splits and not per_lap:
                logs += (
                    f"\nWARNING: Splits for {v.athlete} (bib {v.bib}) don't appear "
                    "to be either cumulative or per-lap; using raw values"
                )
        for lap, split_time in enumerate(split_times, start=1):
            if split_time is not None:
                setattr(v, f"split{lap}", split_time)
        for lap in range(1, v.laps + 1):
            if hasattr(v, f"raw_split{lap}"):
                delattr(v, f"raw_split{lap}")
        delattr(v, "laps")
        if not hasattr(v, "split2"):
            if hasattr(v, "split1"):
                delattr(v, "split1")
        results.append(v)
    results.sort(key=lambda x: x.place)

    return results, logs


def str2dt(rawtime):
    try:
        hours, minutes, seconds = rawtime.split(":")
        minutes = int(minutes)
        seconds = float(seconds)
        if not 0 <= minutes < 60 or not 0 <= seconds < 60:
            raise ValueError
        delta = timedelta(hours=int(hours), minutes=minutes, seconds=seconds)
    except Exception:
        delta = False
    return delta


class Result:
    def __init__(self, place):
        self.place = place

    def __repr__(self):
        return "Result(place={}, athlete={}, guntime={})".format(
            self.place,
            self.athlete,
            self.guntime,
        )
