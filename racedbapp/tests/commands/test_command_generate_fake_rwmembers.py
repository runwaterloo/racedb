import json
from unittest.mock import mock_open, patch

import pytest
from django.core.management import call_command

from racedbapp.models import Rwmember


@pytest.mark.django_db
def test_generate_fake_rwmembers():
    fake_config = {
        "max_results_per_event": 3,
        "male_probability": 0.5,
        "female_probability": 0.4,
        "nonbinary_probability": 0.1,
        "member_photo_url": "https://example.com/photo.jpg",
    }

    m = mock_open(read_data=json.dumps(fake_config))
    with patch("racedbapp.management.commands.generate_fake_rwmembers.open", m):
        call_command("generate_fake_rwmembers")
        assert Rwmember.objects.count() > 0
