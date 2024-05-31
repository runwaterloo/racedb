import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from faker import Faker
from racedbapp.models import Result, Event, Category, Rwmember


class Command(BaseCommand):
    help = "Generate fake data for Result model"

    def handle(self, *args, **kwargs):

        min_num_results = 50
        max_num_results = 300
        num_random_people = 500  # pool of non-members

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

        # Generate a pool of random people who are not in Rwmember
        random_people = []
        while len(random_people) < num_random_people:
            name = faker.name()
            if not Rwmember.objects.filter(name=name).exists():
                random_people.append(name)

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

        # Generate fake data for each event
        events = Event.objects.all()
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
            used_members = (
                set()
            )  # Set to keep track of members already used in this event
            used_random_people = (
                set()
            )  # Set to keep track of random people already used in this event
            for place in range(
                1, num_results + 1
            ):  # Generate 100 results for each event
                rwmember = None  # Placeholder variable for rwmember
                if (
                    random.random() < 0.5
                ):  # Randomly choose between member and non-member
                    rwmember = random.choice(rwmembers)
                    used_members.add(rwmember)  # Add the used member to the set
                    athlete = rwmember.name
                    gender = rwmember.gender
                    # Use member's city if available, else use a fake city
                    city = rwmember.city if rwmember.city else faker.city()
                else:
                    name = random.choice(random_people)
                    while (
                        name in used_random_people
                    ):  # Check if the random person is already used
                        name = random.choice(random_people)
                    used_random_people.add(
                        name
                    )  # Add the used random person to the set
                    athlete = name
                    gender = random.choice(
                        ["F", "M", "NB"]
                    )  # Randomly select gender for non-member
                    city = faker.city()  # Use a fake city for non-member
                bib = faker.bothify(text="??####")
                guntime = guntimes[place - 1]
                chiptime = guntime - timedelta(seconds=random.randint(0, 15))
                # Calculate age based on event date and member's year of birth if rwmember is not None
                age = (
                    event.date.year - rwmember.year_of_birth
                    if rwmember
                    else random.randint(18, 65)
                )
                division = faker.word()
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
