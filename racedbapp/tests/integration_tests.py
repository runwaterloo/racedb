import os
import pytest
from django.test import Client
from . import urls_to_test

"""
Integration tests for the RaceDB application.

These tests are excluded from pytest and Django's test discovery by default,
as they require a live database and specific setup. To run these tests, use the
command:
    pytest racedbapp/tests/integration_tests.py -v
"""

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Override django_db_setup fixture to load SQL dump after test DB is created.
    """
    with django_db_blocker.unblock():
        print("Copying database dump into test DB...")
        with open("racedb/secrets.py", "r") as f:
            lines = f.readlines()
        DB_HOST = [x for x in lines if "DB_HOST" in x][0].split("'")[1]
        DB_PASSWORD = [x for x in lines if "DB_PASSWORD" in x][0].split("'")[1]

        # Import SQL dump directly into test DB
        os.system(
            f"mysqldump --skip-ssl -h {DB_HOST} -u racedb -p{DB_PASSWORD} racedb | "
            f"mysql -h {DB_HOST} -u racedb -p{DB_PASSWORD} test_racedb --ssl=0"
        )

@pytest.mark.django_db
@pytest.mark.parametrize("url", urls_to_test.test_urls)
def test_url(client, url):
    print(f"Testing URL: {url}")
    response = client.get(url)
    assert response.status_code == 200
