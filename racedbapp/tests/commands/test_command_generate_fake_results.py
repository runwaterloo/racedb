from racedbapp.management.commands import generate_fake_results


def test_truncate_country_name():
    # Should truncate if over 50 chars
    long_name = "A" * 60
    assert generate_fake_results.truncate_country_name(long_name) == "A" * 50
    # Should not truncate if under 50 chars
    short_name = "ShortCountry"
    assert generate_fake_results.truncate_country_name(short_name) == short_name
