import pytest
from django.core.cache import cache

from racedbapp.tasks import (
    CACHE_WATCHER_LAST_RUN_KEY,
    CACHE_WATCHER_STATE_KEY,
    db_cache_watcher,
)


@pytest.fixture(autouse=True)
def clear_state():
    for key in (CACHE_WATCHER_STATE_KEY, CACHE_WATCHER_LAST_RUN_KEY, "cache_generation"):
        cache.delete(key)
    yield
    for key in (CACHE_WATCHER_STATE_KEY, CACHE_WATCHER_LAST_RUN_KEY, "cache_generation"):
        cache.delete(key)


@pytest.fixture
def bumps(monkeypatch):
    import racedbapp.tasks as tasks

    seen = []
    monkeypatch.setattr(tasks.cache_lock, "bump_generation", lambda source: seen.append(source))
    return seen


@pytest.fixture
def no_throttle(monkeypatch):
    # beat fires a minute apart; tests run in the same second
    monkeypatch.setattr("racedbapp.tasks._watcher_config_float", lambda name, default: 0.0)


@pytest.fixture
def fingerprint(monkeypatch):
    state = {"value": {"racedbapp_event": (10, 5, 2)}}

    def fake():
        return state["value"]

    monkeypatch.setattr("racedbapp.tasks._get_fingerprint", fake)
    return state


def test_non_postgres_does_nothing(bumps):
    # _get_fingerprint returns None on non-postgres: watcher must not bump
    cache.set(CACHE_WATCHER_STATE_KEY, {"racedbapp_event": (1, 1, 1)}, None)
    db_cache_watcher()
    assert bumps == []


def test_first_run_stores_fingerprint_without_bump(fingerprint, bumps, caplog):
    db_cache_watcher()
    assert cache.get(CACHE_WATCHER_STATE_KEY) == {"racedbapp_event": (10, 5, 2)}
    assert bumps == []


def test_unchanged_fingerprint_does_not_bump(fingerprint, bumps, no_throttle):
    db_cache_watcher()
    db_cache_watcher()
    assert bumps == []


def test_changed_fingerprint_dry_run_does_not_bump(fingerprint, bumps, caplog, no_throttle):
    db_cache_watcher()
    fingerprint["value"] = {"racedbapp_event": (11, 5, 2)}
    with caplog.at_level("INFO", logger="racedbapp.tasks"):
        db_cache_watcher()
    assert bumps == []  # default is dry run
    assert any("DRY RUN" in r.getMessage() and "racedbapp_event" in r.getMessage() for r in caplog.records)


def test_changed_fingerprint_bumps_when_not_dry_run(fingerprint, bumps, monkeypatch, no_throttle):
    monkeypatch.setattr("racedbapp.tasks._watcher_config_bool", lambda name, default: name == "cache_watcher_dry_run" and not default)
    db_cache_watcher()
    fingerprint["value"] = {"racedbapp_event": (11, 6, 2)}
    db_cache_watcher()
    assert bumps == ["watcher"]


def test_interval_throttle_skips_run(fingerprint, bumps, monkeypatch):
    monkeypatch.setattr("racedbapp.tasks._watcher_config_float", lambda name, default: 600.0)
    db_cache_watcher()
    fingerprint["value"] = {"racedbapp_event": (11, 5, 2)}
    db_cache_watcher()
    assert bumps == []  # throttled: fingerprint comparison never happened
    # last_run was still written by the throttled... no: only first run wrote it


def test_failed_fingerprint_no_bump(fingerprint, bumps, no_throttle):
    db_cache_watcher()
    cache.set(CACHE_WATCHER_STATE_KEY, {"racedbapp_event": (1, 1, 1)}, None)
    db_cache_watcher()
    assert bumps == []


