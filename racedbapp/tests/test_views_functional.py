from django.test import TestCase
from django.test import Client
import os
from ..models import Race
from . import urls_to_test


def setUpModule():
    """ Import the actual database """
    print("Copying production database...")
    os.system("mysqldump -h racedb_db -u racedb -p`cat /run/secrets/MYSQL_PASSWORD_FILE` racedb | mysql -h racedb_db -u racedb -p`cat /run/secrets/MYSQL_PASSWORD_FILE` test_racedb")


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
