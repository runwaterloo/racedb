"""Settings per-environment regression tests.

The unconditional `CELERY_BROKER_URL` default that clobbered the dev
branch's racedbdev-redis broker (#437) is the class of bug these tests
guard against: assert the broker/cache URL for each SETTINGS value by
importing the settings module in a fresh subprocess per env.
"""

import json
import os
import subprocess
import sys

import pytest

PROD_BROKER = "redis://racedb-redis:6379"
DEV_BROKER = "redis://racedbdev-redis:6379"

EXPECTED = {
    "prod": {"broker": PROD_BROKER, "cache": "redis://racedb-redis:6379/1"},
    "dev": {"broker": DEV_BROKER, "cache": "redis://racedbdev-redis:6379/1"},
    "min": {"broker": PROD_BROKER, "cache": None},  # locmem cache
}


@pytest.mark.parametrize("env_name", ["prod", "dev", "min"])
def test_broker_and_cache_per_settings_env(env_name):
    env = dict(os.environ)
    env["SETTINGS"] = env_name
    env.pop("PYTEST_CURRENT_TEST", None)
    code = (
        "import json;"
        "from django.conf import settings as s;"
        "import django; django.setup();"
        "print(json.dumps({"
        "'broker': s.CELERY_BROKER_URL,"
        "'cache': s.CACHES['default']['LOCATION']"
        "}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )
    assert result.returncode == 0, result.stderr
    got = json.loads(result.stdout.strip().splitlines()[-1])
    assert got["broker"] == EXPECTED[env_name]["broker"]
    if EXPECTED[env_name]["cache"] is not None:
        assert got["cache"] == EXPECTED[env_name]["cache"]
