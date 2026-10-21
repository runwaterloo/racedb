from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "db_cache_watcher": {
        "task": "racedbapp.tasks.db_cache_watcher",
        "schedule": crontab(minute="*"),
    },
    "heartbeat": {
        "task": "racedbapp.tasks.heartbeat",
        "schedule": crontab(minute="*/15"),
    },
    "photoupdate": {
        "task": "racedbapp.tasks.photoupdate",
        "schedule": crontab(minute="54"),
        "kwargs": {"request_date": "auto"},
    },
    "update_featured_member_id": {
        "task": "racedbapp.tasks.update_featured_member_id",
        "schedule": crontab(hour="0", minute="0"),
    },
    "slack_featured_member": {
        "task": "racedbapp.tasks.slack_featured_member",
        "schedule": crontab(hour="0", minute="1"),
    },
    "slack_missing_urls": {
        "task": "racedbapp.tasks.slack_missing_urls",
        "schedule": crontab(hour="20", minute="0"),
    },
}
