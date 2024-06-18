import os

from django.test import Client, TestCase

from ..models import Race
from . import urls_to_test


def setUpModule():
    """ Import the actual database """
    print("Copying production database...")
    with open("racedb/secrets.py", "r") as f:
        lines = f.readlines()
    DB_HOST = [x for x in lines if "DB_HOST" in x][0].split("'")[1]
    DB_PASSWORD = [x for x in lines if "DB_PASSWORD" in x][0].split("'")[1]
    os.system(
        "mysqldump -h {0} -u racedb -p{1} racedb | mysql -h {0} -u racedb -p{1} test_racedb".format(
            DB_HOST, DB_PASSWORD
        )
    )


class SimpleTest(TestCase):
    """ Simply test if views return status 200 """

    def setUp(self):
        self.client = Client()

    def test_details(self):
        for u in urls_to_test.test_urls:
            print("Testing {}".format(u))
            response = self.client.get(u)
            self.assertEqual(response.status_code, 200)
        print("{} URLs tested!".format(len(urls_to_test.test_urls)))
