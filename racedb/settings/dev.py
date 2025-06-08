from racedb import celery_beats

from .base import *  # noqa

DEBUG = True

STATIC_URL = "/static/"
STATIC_ROOT = "/static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://racedbdev-redis:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": None,
    }
}

CELERY_BROKER_URL = "redis://racedbdev-redis:6379"
CELERY_RESULT_BACKEND = "redis://racedbdev-redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = celery_beats.CELERY_BEAT_SCHEDULE

CSRF_TRUSTED_ORIGINS = ["https://racedb.runwaterloo.com", "https://racedb-api.runwaterloo.com"]
