from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'heartbeat': {
        'task': 'racedbapp.tasks.heartbeat',
        'schedule': crontab(minute="*/15")
    },
    'photoupdate': {
        'task': 'racedbapp.tasks.photoupdate',
        'schedule': crontab(minute="54")
    },
}
