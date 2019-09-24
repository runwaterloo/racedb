from django.test import TestCase
from django.test import Client
import os
from ..models import Race
from . import urls_to_test


def setUpModule():
    """ Import the actual database """
    print("Copying production database...")
    with open("racedb/secrets.py", "r") as f:
        lines = f.readlines()
    DB_PASSWORD = [x for x in lines if "DB_PASSWORD" in x][0].split("'")[1]
    os.system("mysqldump -h racedb_db -u racedb -p{0} racedb | mysql -h racedb_db -u racedb -p{0} test_racedb".format(DB_PASSWORD))


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

    def test_logos(self):
        """ Test that a race logo file exists for all races """
        races = Race.objects.all()
        slugs = [x.slug for x in races]
        files = os.listdir("racedbapp/static/race_logos")
        for slug in slugs:
            assert "{}.png".format(slug) in files
