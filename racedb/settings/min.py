import os

from racedb import celery_beats

from .base import *  # noqa

DEBUG = True
ENABLE_DEBUG_TOOLBAR = True

if os.getenv("DISABLE_DEBUG_TOOLBAR", "false") == "true":
    ENABLE_DEBUG_TOOLBAR = False

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS += ("debug_toolbar",)  # noqa
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ] + MIDDLEWARE  # noqa
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }
    INTERNAL_IPS = ["127.0.0.1", "::1"]


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
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

CELERY_BROKER_URL = "redis://racedb_redis:6379"
CELERY_RESULT_BACKEND = "redis://racedb_redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = celery_beats.CELERY_BEAT_SCHEDULE
