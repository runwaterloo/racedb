from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
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
}
