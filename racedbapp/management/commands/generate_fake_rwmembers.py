import random
from datetime import datetime
from django.core.management.base import BaseCommand
from faker import Faker
from racedbapp.models import Rwmember

class Command(BaseCommand):
    help = 'Generate fake data for Rwmember model'

    def handle(self, *args, **kwargs):
        faker = Faker()

        # Clear existing data
        Rwmember.objects.all().delete()

        # Generate fake data
        for _ in range(100):  # Adjust the number of entries as needed
            name = faker.name()
            slug = faker.slug()
            gender = random.choice([choice[0] for choice in Rwmember.GENDER_CHOICES])
            year_of_birth = faker.year()
            city = faker.city()
            joindate = faker.date_between(start_date='-10y', end_date='today')
            photourl = faker.image_url()
            altname = faker.name()
            active = faker.boolean()
            hasphotos = faker.boolean()

            member = Rwmember.objects.create(
                name=name,
                slug=slug,
                gender=gender,
                year_of_birth=year_of_birth,
                city=city,
                joindate=joindate,
                photourl=photourl,
                altname=altname,
                active=active,
                hasphotos=hasphotos,
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated 100 fake Rwmember entries'))
