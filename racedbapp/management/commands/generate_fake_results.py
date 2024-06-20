import json
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from faker import Faker
from racedbapp.models import Result, Event, Category, Rwmember


class Command(BaseCommand):
    help = "Generate fake data for Result model"

    def handle(self, *args, **kwargs):

        with open("racedbapp/management/commands/fake_config.json") as f:
            fake_config = json.load(f)
        min_num_results = fake_config["min_results_per_event"]
        max_num_results = fake_config["max_results_per_event"]
        num_random_people = int(
            fake_config["max_results_per_event"] * 1.5
        )  # pool of non-members

        faker = Faker()

        # Clear existing data
        Result.objects.all().delete()
        Category.objects.all().delete()

        # Get existing foreign key data
        rwmembers = list(Rwmember.objects.all())

        # Ensure there are enough rwmembers
        if not rwmembers:
            self.stdout.write(self.style.ERROR("No Rwmembers found."))
            return

        # Gender choices with weights
        gender_choices = [choice[0] for choice in Rwmember.GENDER_CHOICES]
        gender_weights = [
            fake_config["male_probability"],
            fake_config["female_probability"],
            fake_config["nonbinary_probability"],
        ]

        # Generate a pool of random people who are not in Rwmember
        used_names = []
        random_people = {}
        while len(random_people) < num_random_people:
            gender = random.choices(gender_choices, weights=gender_weights, k=1)[0]
            if gender == "M":
                name = faker.name_male()
            elif gender == "F":
                name = faker.name_female()
            else:
                name = faker.name()
            name = faker.name()
            if Rwmember.objects.filter(name=name).exists():
                continue
            if name in used_names:
                continue
            used_names.append(name)
            city = faker.city()
            random_people[name] = {"gender": gender, "city": city}

        # Helper function to create category based on gender and age
        def get_or_create_category(gender, age):
            age_group = (age // 10) * 10
            category_name = f"{gender}{age_group}-{age_group + 9}"
            category, created = Category.objects.get_or_create(name=category_name)
            return category

        # Helper function to truncate country names if they exceed 50 characters
        def truncate_country_name(country):
            if len(country) > 50:
                return country[:50]
            return country

        # Generate fake data for past events
        today = datetime.today().date()
        events = Event.objects.filter(date__lte=today)
        for event in events:
            num_results = random.randint(min_num_results, max_num_results)
            # generate chip times
            guntimes = []
            for i in range(0, num_results):
                guntimes.append(
                    timedelta(
                        seconds=random.randint(1800, 6600)
                        * float(event.distance.km)
                        / 10
                    )
                )
            guntimes = sorted(guntimes)

            # Dictionary to keep track of counts for each gender and category
            gender_counts = {"F": 0, "M": 0, "NB": 0}
            category_counts = {}
            used_members = set()
            used_random_people = set()
            used_bibs = set()
            for place in range(1, num_results + 1):
                rwmember = None  # Placeholder variable for rwmember
                if random.random() < 0.5:
                    rwmember = random.choice(rwmembers)
                    while rwmember in used_members:
                        rwmember = random.choice(rwmembers)
                    used_members.add(rwmember)  # Add the used member to the set
                    athlete = rwmember.name
                    gender = rwmember.gender
                    city = rwmember.city
                else:
                    name = random.choice(list(random_people.keys()))
                    while name in used_random_people:
                        name = random.choice(list(random_people.keys()))
                    used_random_people.add(name)
                    athlete = name
                    gender = random_people[name]["gender"]
                    city = random_people[name]["city"]
                bib = random.randint(1, num_results * 5)
                while bib in used_bibs:
                    bib = random.randint(1, num_results * 5)
                used_bibs.add(bib)
                guntime = guntimes[place - 1]
                chiptime = guntime - timedelta(seconds=random.randint(0, 15))
                # Calculate age based on event date and member's year of birth if rwmember is not None
                age = (
                    event.date.year - rwmember.year_of_birth
                    if rwmember
                    else random.randint(5, 85)
                )
                division = ""
                province = faker.state()
                country = truncate_country_name(
                    faker.country()
                )  # Truncate country name if it exceeds 50 characters
                isrwpb = faker.boolean()

                # Increment gender count and assign gender place
                gender_counts[gender] += 1
                gender_place = gender_counts[gender]

                # Get or create category based on gender and age
                category = get_or_create_category(gender, age)

                # Increment category count and assign category place
                category_key = (
                    f"{gender}{age // 10}"  # Key for category count dictionary
                )
                if category_key not in category_counts:
                    category_counts[category_key] = 0
                category_counts[category_key] += 1
                category_place = category_counts[category_key]

                Result.objects.create(
                    event=event,
                    category=category,
                    athlete=athlete,
                    gender=gender,
                    city=city,
                    place=place,
                    bib=bib,
                    chiptime=chiptime,
                    guntime=guntime,
                    age=age,
                    division=division,
                    province=province,
                    country=country,
                    rwmember=rwmember if rwmember in used_members else None,
                    gender_place=gender_place,
                    category_place=category_place,
                    isrwpb=isrwpb,
                )

        self.stdout.write(
            self.style.SUCCESS("Successfully generated results for all events")
        )
