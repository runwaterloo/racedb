from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.db import models

from racedbapp import process_photoupdate, signals


def test_tags_changed_ignores_order():
    assert not process_photoupdate.tags_changed(["1", "2", "3"], ["3", "1", "2"])
    assert process_photoupdate.tags_changed([1, 2], [1, 2, 3])
    assert process_photoupdate.tags_changed([], ["1"])


def test_clear_cache_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(signals.settings, "CACHE_SIGNALS_ENABLED", False)
    enqueue = Mock()
    monkeypatch.setattr(signals.tasks, "safe_enqueue", enqueue)
    signals._clear_cache("test_source")
    enqueue.assert_not_called()


def test_clear_cache_enqueues_when_enabled(monkeypatch):
    monkeypatch.setattr(signals.settings, "CACHE_SIGNALS_ENABLED", True)
    enqueue = Mock()
    monkeypatch.setattr(signals.tasks, "safe_enqueue", enqueue)
    signals._clear_cache("test_source")
    enqueue.assert_called_once()


@pytest.mark.django_db
def test_event_save_enqueues_clear(create_event, monkeypatch):
    called = []
    monkeypatch.setattr(signals, "_clear_cache", lambda source: called.append(source))
    event = create_event()
    event.youtubeurl = "https://youtube.com/x"
    event.save()
    assert "event_save" in called


@pytest.mark.django_db
def test_member_save_enqueues_clear(create_rwmember, monkeypatch):
    called = []
    monkeypatch.setattr(signals, "_clear_cache", lambda source: called.append(source))
    member = create_rwmember()
    member.name = "Test Change"
    member.save()
    assert "member_save" in called


@pytest.mark.django_db
def test_config_raw_save_skips_clear(create_event, monkeypatch):
    called = []
    monkeypatch.setattr(signals, "_clear_cache", lambda source: called.append(source))
    from racedbapp.models import Config

    config = Config(name="test_cfg", value="x")
    config.save()
    assert "config_save" in called
    signals.config_post_save(sender=Config, instance=config, raw=True)
    assert called.count("config_save") == 1
