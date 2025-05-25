import json
import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from faker import Faker

from racedbapp.models import Category, Event, Result, Rwmember


class Command(BaseCommand):
    help = "Generate fake data for Result model"

    def handle(self, *args, **kwargs):
        fake_config = load_fake_config("racedbapp/management/commands/fake_config.json")
        min_num_results = fake_config["min_results_per_event"]
        max_num_results = fake_config["max_results_per_event"]
        num_random_people = int(fake_config["max_results_per_event"] * 1.5)
        faker = Faker()
        Result.objects.all().delete()
        Category.objects.all().delete()
        rwmembers = list(Rwmember.objects.all())
        if not rwmembers:
            self.stdout.write(self.style.ERROR("No Rwmembers found."))
            return
        gender_choices = [choice[0] for choice in Rwmember.GENDER_CHOICES]
        gender_weights = [
            fake_config["male_probability"],
            fake_config["female_probability"],
            fake_config["nonbinary_probability"],
        ]
        used_names = []
        random_people = generate_random_people(
            faker, num_random_people, gender_choices, gender_weights, used_names
        )
        today = datetime.today().date()
        events = Event.objects.filter(date__lte=today)
        for event in events:
            generate_results_for_event(
                event, min_num_results, max_num_results, rwmembers, random_people, faker
            )
        self.stdout.write(self.style.SUCCESS("Successfully generated results for all events"))


def load_fake_config(path):
    with open(path) as f:
        return json.load(f)


def generate_random_people(faker, num_random_people, gender_choices, gender_weights, used_names):
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
    return random_people


def get_or_create_category(gender, age):
    age_group = (age // 10) * 10
    category_name = f"{gender}{age_group}-{age_group + 9}"
    category, created = Category.objects.get_or_create(name=category_name)
    return category


def truncate_country_name(country):
    if len(country) > 50:
        return country[:50]
    return country


def generate_results_for_event(
    event, min_num_results, max_num_results, rwmembers, random_people, faker
):
    num_results = random.randint(min_num_results, max_num_results)
    guntimes = [
        timedelta(seconds=random.randint(1800, 6600) * float(event.distance.km) / 10)
        for _ in range(num_results)
    ]
    guntimes = sorted(guntimes)
    gender_counts = {"F": 0, "M": 0, "NB": 0}
    category_counts = {}
    used_members = set()
    used_random_people = set()
    used_bibs = set()
    for place in range(1, num_results + 1):
        rwmember = None
        if random.random() < 0.5:
            rwmember = random.choice(rwmembers)
            while rwmember in used_members:
                rwmember = random.choice(rwmembers)
            used_members.add(rwmember)
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
        age = event.date.year - rwmember.year_of_birth if rwmember else random.randint(5, 85)
        division = ""
        province = faker.state()
        country = truncate_country_name(faker.country())
        isrwpb = faker.boolean()
        gender_counts[gender] += 1
        gender_place = gender_counts[gender]
        category = get_or_create_category(gender, age)
        category_key = f"{gender}{age // 10}"
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
