from django.test import TestCase
from django.test import Client
import os
from . import urls_to_test

class SimpleTest(TestCase):
    """ Simply test if views return status 200 """
    def setUp(self):
        self.client = Client()
        print('Copying production database...')
        os.system("sudo mysqldump racedb | sudo mysql test_racedb")
    def test_details(self):
        for u in urls_to_test.test_urls:
            print('Testing {}'.format(u))
            response = self.client.get(u)
            self.assertEqual(response.status_code, 200)
        print('{} URLs tested!'.format(len(urls_to_test.test_urls)))
