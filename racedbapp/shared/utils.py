from datetime import timedelta
from pathlib import Path

def truncate_time(time):
    try:
        int(time)
    except:
        trunc_time = time - timedelta(microseconds=time.microseconds)
    else:
        ustime = timedelta(microseconds=time)
        trunc_time = ustime - timedelta(microseconds=ustime.microseconds)
    return trunc_time

def get_race_logo_slug(slug):
    file_path = Path(f"racedbapp/static/race_logos/{slug}.png")
    if not file_path.is_file():
        slug = "rw-race-logo"
    return slug
