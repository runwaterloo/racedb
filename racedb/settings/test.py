import importlib

from django.db.backends.signals import connection_created

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

STATIC_URL = "/static/"

# Copy all attributes from base except those overridden above
for attr in dir(base):
    if not attr.startswith("_") and attr not in globals():
        globals()[attr] = getattr(base, attr)


# Enable foreign key enforcement in SQLite during tests
def activate_foreign_keys(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")


connection_created.connect(activate_foreign_keys)
