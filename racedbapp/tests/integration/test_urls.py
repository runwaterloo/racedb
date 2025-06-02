import json
import os

import pytest

# Load URLs from the JSON file
with open(os.path.join(os.path.dirname(__file__), "urls_to_test.json")) as f:
    test_urls = json.load(f)

"""
Integration tests for the RaceDB application.

These tests are excluded from pytest and Django's test discovery by default,
as they require a live database and specific setup. To run these tests, typicall from
inside a running container, use the command:

    pytest -m integration

Or to run all tests, unit and integration:

    pytest -m "integration or not integration"
"""


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Override django_db_setup fixture to load SQL dump after test DB is created.
    """
    with django_db_blocker.unblock():
        print("Copying database dump into test DB...")
        with open("racedb/secrets.py") as f:
            lines = f.readlines()
        DB_HOST = [x for x in lines if "DB_HOST" in x][0].split("'")[1]
        DB_PASSWORD = [x for x in lines if "DB_PASSWORD" in x][0].split("'")[1]

        # Import SQL dump directly into test DB
        os.system(
            f"mysqldump --skip-ssl -h {DB_HOST} -u racedb -p{DB_PASSWORD} racedb | "
            f"mysql -h {DB_HOST} -u racedb -p{DB_PASSWORD} test_racedb --ssl=0"
        )


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.parametrize("url", test_urls)
def test_url(client, url):
    print(f"Testing URL: {url}")
    response = client.get(url)
    assert response.status_code == 200
