"""
Django settings for racedb project.

Per environemnt separation inspired by:
https://simpleisbetterthancomplex.com/tips/2017/07/03/django-tip-20-working-with-multiple-settings-modules.html
"""

import os

from racedb import celery_beats, secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = secrets.SECRET_KEY
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = (
    "django_prometheus",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "racedbapp",
    "django_slack",
    "django_s3_storage",
)

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = "racedb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "racedb.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": secrets.DB_NAME,
        "USER": secrets.DB_USER,
        "PASSWORD": secrets.DB_PASSWORD,
        "HOST": secrets.DB_HOST,
        "OPTIONS": {"init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Toronto"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s "
            "[%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "loggers": {
        "django": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
        "racedbapp": {"handlers": ["console"], "propagate": False, "level": "DEBUG"},
    },
}

EMAIL_HOST = secrets.EMAIL_HOST
EMAIL_HOST_USER = secrets.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = secrets.EMAIL_HOST_PASSWORD
EMAIL_PORT = 587
EMAIL_USE_TLS = True

SLACK_TOKEN = secrets.SLACK_TOKEN
SLACK_CHANNEL = "#notifications"
SLACK_BACKEND = "django_slack.backends.CeleryBackend"
SLACK_USERNAME = "giskard"
SLACK_ICON_EMOJI = ":robot_face:"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
