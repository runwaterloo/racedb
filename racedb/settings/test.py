import importlib

base = importlib.import_module("racedb.settings.base")

DEBUG = True

# Use in-memory SQLite database for fast, DB-server-free testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Optionally, speed up password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Optionally, reduce logging noise
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

# Copy all attributes from base except those overridden above
for attr in dir(base):
    if not attr.startswith("_") and attr not in globals():
        globals()[attr] = getattr(base, attr)
