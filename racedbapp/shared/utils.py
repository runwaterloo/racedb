from datetime import timedelta
from pathlib import Path


def truncate_time(time):
    try:
        int(time)
    except Exception:
        trunc_time = time - timedelta(microseconds=time.microseconds)
    else:
        ustime = timedelta(microseconds=time)
        trunc_time = ustime - timedelta(microseconds=ustime.microseconds)
    return trunc_time


def get_race_logo_slug(slug):
    if isinstance(slug, str):
        file_path = Path(f"racedbapp/static/race_logos/{slug}.png")
        if not file_path.is_file():
            slug = "rw-race-logo"
    else:
        slug = "rw-race-logo"
    return slug


def get_achievement_image(slug, badge):
    file_path = Path(f"racedbapp/static/achievements/{badge}-{slug}.png")
    if file_path.is_file():
        image = f"{badge}-{slug}.png"
    else:
        image = "generic_100x100.png"
    return image
