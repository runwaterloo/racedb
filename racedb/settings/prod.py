from racedb import celery_beats

from .base import *  # noqa

DEBUG = False

AWS_ACCESS_KEY_ID = secrets.RACEDB_STATIC_AWS_ACCESS_KEY_ID  # noqa
AWS_SECRET_ACCESS_KEY = secrets.RACEDB_STATIC_AWS_SECRET_ACCESS_KEY  # noqa
AWS_S3_BUCKET_NAME_STATIC = "racedb-static"
AWS_S3_MAX_AGE_SECONDS = "315360000"
STATICFILES_STORAGE = "django_s3_storage.storage.ManifestStaticS3Storage"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://racedb-redis:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": None,
    }
}

CELERY_BROKER_URL = "redis://racedb-redis:6379"
CELERY_RESULT_BACKEND = "redis://racedb-redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = celery_beats.CELERY_BEAT_SCHEDULE

CSRF_TRUSTED_ORIGINS = ["https://results.runwaterloo.com"]
