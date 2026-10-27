import json
from unittest.mock import mock_open, patch

import pytest
from django.core.management import call_command

from racedbapp.models import Config, Event, Rwmember, Rwmembertag


@pytest.mark.django_db
def test_generate_fake_boost():
    fake_config = {
        "boost_year": 2026,
        "boost_tagged_fraction": 0.5,
        "boost_config": {"boost_leaderboard_size": 10},
    }
    Rwmembertag.objects.create(name="Member")
    Rwmember.objects.create(
        name="Boost Test Member", slug="boost-test-member", gender="M", year_of_birth=1980
    )

    m = mock_open(read_data=json.dumps(fake_config))
    with patch("racedbapp.management.commands.generate_fake_boost.open", m):
        call_command("generate_fake_boost")

    tag = Rwmembertag.objects.get(name="boost-2026")
    member = Rwmember.objects.get(name="Boost Test Member")
    assert tag in member.tags.all()
    assert Config.objects.get(name="boost_leaderboard_size").value == "10"
    assert Event.objects.filter(date__year=2026).count() > 0


@pytest.mark.django_db
def test_generate_fake_boost_idempotent():
    fake_config = {
        "boost_year": 2026,
        "boost_tagged_fraction": 0.5,
        "boost_config": {"boost_leaderboard_size": 10},
    }
    Rwmembertag.objects.create(name="Member")
    Rwmember.objects.create(
        name="Boost Test Member", slug="boost-test-member", gender="M", year_of_birth=1980
    )

    m = mock_open(read_data=json.dumps(fake_config))
    with patch("racedbapp.management.commands.generate_fake_boost.open", m):
        call_command("generate_fake_boost")
        call_command("generate_fake_boost")

    assert Rwmembertag.objects.filter(name="boost-2026").count() == 1
    assert Config.objects.filter(name="boost_leaderboard_size").count() == 1
