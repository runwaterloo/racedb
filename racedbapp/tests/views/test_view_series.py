import pytest
from rest_framework.test import APIClient

from racedbapp.models import Result
from racedbapp.view_series import set_ismaster_from_result


@pytest.mark.django_db
def test_series_endpoint_missing():
    client = APIClient()
    url = "/series/does-not-exist/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_series_endpoint_success(create_series):
    client = APIClient()
    series = create_series()
    url = f"/series/{series.slug}/"
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_series_endpoint_with_filter(create_series):
    client = APIClient()
    series = create_series()
    first_result = Result.objects.first()
    first_result.age = 40
    first_result.save()
    for filter in (
        "Female",
        "Male",
        "Masters",
        "F-Masters",
        "M-Masters",
        "some-category",
    ):
        url = f"/series/{series.slug}/?filter={filter}"
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_age_grade_mode_ranks_descending_and_shows_column(create_age_grade_series):
    client = APIClient()
    series = create_age_grade_series()
    response = client.get(f"/series/{series.slug}/?scoring=age-grade")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Total Age Grade" in content  # age-grade table header
    results = response.context["results"]
    totals = [r.total_age_grade for r in results]
    assert totals == sorted(totals, reverse=True)
    # Displayed per-event grades sum to the total (round-then-sum).
    for result in results:
        assert result.total_age_grade == pytest.approx(sum(result.times))


@pytest.mark.django_db
def test_age_grade_param_on_disabled_series_falls_back_to_total_time(create_series):
    client = APIClient()
    series = create_series(age_grade_enabled=False)
    response = client.get(f"/series/{series.slug}/?scoring=age-grade")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Total Age Grade" not in content
    assert "Total Time" in content
    assert response.context["scoring"] is None


@pytest.mark.django_db
def test_toggle_visibility_tracks_flag(create_age_grade_series, create_series):
    client = APIClient()
    enabled = create_age_grade_series()
    enabled_content = client.get(f"/series/{enabled.slug}/").content.decode()
    assert "scoring=age-grade" in enabled_content  # toggle link present

    disabled = create_series(age_grade_enabled=False)
    disabled_content = client.get(f"/series/{disabled.slug}/").content.decode()
    assert "scoring=age-grade" not in disabled_content


@pytest.mark.django_db
def test_filters_stack_with_age_grade_mode(create_age_grade_series):
    client = APIClient()
    series = create_age_grade_series()
    response = client.get(f"/series/{series.slug}/?scoring=age-grade&filter=Male")
    assert response.status_code == 200
    results = response.context["results"]
    assert results  # not empty
    assert all(r.gender == "M" for r in results)


@pytest.mark.django_db
def test_membership_rule_excludes_athlete_missing_an_event(create_age_grade_series):
    client = APIClient()
    series = create_age_grade_series()
    response = client.get(f"/series/{series.slug}/?scoring=age-grade")
    athletes = [r.athlete for r in response.context["results"]]
    assert "Missing Event" not in athletes  # only in event one
    assert len(athletes) == 4


@pytest.mark.django_db
def test_missing_age_athlete_retained(create_age_grade_series):
    client = APIClient()
    series = create_age_grade_series()
    response = client.get(f"/series/{series.slug}/?scoring=age-grade")
    athletes = [r.athlete for r in response.context["results"]]
    assert "Unknown Age" in athletes  # no age, no year_of_birth, still ranked


@pytest.mark.django_db
def test_set_ismaster_from_result(create_result):
    result = create_result()
    scenarios = [
        {"age": None, "category_ismasters": False, "expected_result": False},
        {"age": None, "category_ismasters": True, "expected_result": True},
        {"age": 39, "category_ismasters": False, "expected_result": False},
        {"age": 39, "category_ismasters": True, "expected_result": False},
        {"age": 40, "category_ismasters": False, "expected_result": True},
        {"age": 40, "category_ismasters": True, "expected_result": True},
    ]
    for scenario in scenarios:
        result.age = scenario["age"]
        result.category.ismasters = scenario["category_ismasters"]
        result.save()
        assert set_ismaster_from_result(result) is scenario["expected_result"]
