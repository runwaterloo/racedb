import os
import sys

from django.db.backends.signals import connection_created

from racedb import celery_beats, secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Core Django settings ---
SECRET_KEY = secrets.SECRET_KEY

# Set DEBUG False by default, unless envar DEBUG=true set
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["*"]

# Hosts gated behind Django auth (QaAuthGateMiddleware): unauthenticated
# requests get a 401. Production (results.runwaterloo.com) is not listed.
QA_AUTH_HOSTS = ["racedb.runwaterloo.com"]

# --- Installed apps ---
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
    "rest_framework",
    "rest_framework.authtoken",
)

# --- Middleware ---
MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "racedbapp.middleware.QaAuthGateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# --- URL and WSGI ---
ROOT_URLCONF = "racedb.urls"
WSGI_APPLICATION = "racedb.wsgi.application"

# --- Templates ---
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

# --- Database ---
if os.getenv("DATABASE", "sqlite3") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", secrets.DB_NAME),
            "USER": os.getenv("DB_USER", secrets.DB_USER),
            "PASSWORD": os.getenv("DB_PASSWORD", secrets.DB_PASSWORD),
            "HOST": os.getenv(
                "DB_HOST", secrets.DB_HOST if hasattr(secrets, "DB_HOST") else "postgres"
            ),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Toronto"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = "/static/"
STATIC_ROOT = "/static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# --- Env-specific ---
if os.getenv("SETTINGS", "none") == "prod":
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
    CSRF_TRUSTED_ORIGINS = [
        "https://results.runwaterloo.com",
        "https://api.runwaterloo.com",
    ]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
elif os.getenv("SETTINGS", "none") == "dev":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://racedbdev-redis:6379/1",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "TIMEOUT": 5,
        }
    }
    CELERY_BROKER_URL = "redis://racedbdev-redis:6379"
    CELERY_RESULT_BACKEND = "redis://racedbdev-redis:6379"
    CSRF_TRUSTED_ORIGINS = [
        "https://racedb.runwaterloo.com",
        "https://racedb-api.runwaterloo.com",
    ]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "whitenoise.middleware.WhiteNoiseMiddleware"]
    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "TIMEOUT": 5,
        }
    }

# --- Celery ---
# Default broker for SETTINGS=min (local docker compose): the compose redis.
# prod/dev set their own CELERY_BROKER_URL above.
CELERY_BROKER_URL = "redis://racedb-redis:6379"
# Under pytest, swap in an in-memory broker so safe_enqueue()'s task.delay()
# succeeds instantly instead of kombu retrying against redis/amqp for ~0.6s
# per enqueue (Config-save tests were paying this on every Config.create).
if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
    CELERY_BROKER_URL = "memory://"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Watcher fires every minute; without this, its task results (celery-task-meta-*)
# accumulate in Redis at the 24 h default (~1500 keys). Nothing reads them —
# keep a short TTL so they're only there if someone goes looking.
CELERY_TASK_RESULT_EXPIRES = 3600
CELERY_BEAT_SCHEDULE = celery_beats.CELERY_BEAT_SCHEDULE

# --- Logging ---
if os.getenv("SETTINGS", "test") in ("prod", "dev", "min"):
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
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
else:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }


# --- Email ---
EMAIL_HOST = secrets.EMAIL_HOST
EMAIL_HOST_USER = secrets.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = secrets.EMAIL_HOST_PASSWORD
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# --- Slack ---
SLACK_TOKEN = secrets.SLACK_TOKEN
SLACK_CHANNEL = "#notifications"
SLACK_BACKEND = "django_slack.backends.CeleryBackend"
SLACK_USERNAME = "giskard"
SLACK_ICON_EMOJI = ":robot_face:"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "racedbapp.api.v1.exceptions.custom_exception_handler",
}

# --- Django model defaults ---
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Skip the debug toolbar under pytest: it injects a random per-request ID into
# every response, so a response that comes back from the cache differs from the
# one that was originally rendered.
ENABLE_DEBUG_TOOLBAR = (
    os.getenv("ENABLE_DEBUG_TOOLBAR", "false") == "true"
    and "pytest" not in sys.modules
)

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS += ("debug_toolbar",)  # noqa
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ] + MIDDLEWARE  # noqa
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }
    INTERNAL_IPS = ["127.0.0.1", "::1"]

if os.getenv("SETTINGS", "none") not in ("prod", "dev"):
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]


# Enable foreign key enforcement in SQLite during tests
def activate_foreign_keys(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")


connection_created.connect(activate_foreign_keys)
