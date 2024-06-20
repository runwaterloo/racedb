import random
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker
from racedbapp.models import Rwmember
import json


class Command(BaseCommand):
    help = "Generate fake data for Rwmember model"

    def handle(self, *args, **kwargs):

        with open("racedbapp/management/commands/fake_config.json") as f:
            fake_config = json.load(f)
        num_members = int(fake_config["max_results_per_event"] * 1.1)

        faker = Faker()

        # Clear existing data
        Rwmember.objects.all().delete()

        # Gender choices with weights
        gender_choices = [choice[0] for choice in Rwmember.GENDER_CHOICES]
        gender_weights = [
            fake_config["male_probability"],
            fake_config["female_probability"],
            fake_config["nonbinary_probability"],
        ]

        # Generate fake data
        unique_names = set()
        while len(unique_names) < num_members:
            gender = random.choices(gender_choices, weights=gender_weights, k=1)[0]
            if gender == "M":
                name = faker.name_male()
            elif gender == "F":
                name = faker.name_female()
            else:
                name = faker.name()
            if name in unique_names:
                continue
            unique_names.add(name)
            slug = slugify(name)
            year_of_birth = faker.date_between(start_date="-90y", end_date="-1y").year
            city = faker.city()
            joindate = faker.date_between(start_date="-10y", end_date="today")
            photourl = fake_config["member_photo_url"]
            altname = ""
            active = random.choices([True, False], weights=[0.9, 0.1], k=1)[0]
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {num_members} fake Rwmember entries"
            )
        )
