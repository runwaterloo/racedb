from .base import *

DEBUG = True

STATIC_URL = "/static/"
STATIC_ROOT = "/static/"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://racedb_redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "TIMEOUT": None,
    }
}

CELERY_BROKER_URL = "redis://racedb_redis:6379"
CELERY_RESULT_BACKEND = "redis://racedb_redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = celery_beats.CELERY_BEAT_SCHEDULE