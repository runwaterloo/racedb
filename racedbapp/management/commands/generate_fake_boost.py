import json
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from racedbapp.models import Config, Distance, Event, Race, Rwmember, Rwmembertag

RACE_NAMES = [
    ("Boost Marathon", "BM", 42.195),
    ("Boost Half Marathon", "BHM", 21.1),
    ("Boost 10 Kilometre", "B10K", 10),
    ("Boost 5 Kilometre", "B5K", 5),
]


class Command(BaseCommand):
    help = (
        "Seed data needed for the boost pages (boost tag, member tagging, "
        "config values, and events for the boost year if none exist)"
    )

    def handle(self, *args, **kwargs):
        fake_config = load_fake_config("racedbapp/management/commands/fake_config.json")
        year = fake_config["boost_year"]
        tag, _ = Rwmembertag.objects.get_or_create(name=f"boost-{year}")
        members = list(Rwmember.objects.filter(year_of_birth__isnull=False, gender__in=["M", "F"]))
        num_tagged = max(1, int(len(members) * fake_config["boost_tagged_fraction"]))
        random.shuffle(members)
        for member in members[:num_tagged]:
            member.tags.add(tag)
        for name, default in fake_config["boost_config"].items():
            Config.objects.update_or_create(name=name, defaults={"value": str(default)})
        num_events = self.create_events(year)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully tagged {num_tagged} members with boost-{year}, "
                f"seeded boost config values, and created {num_events} events"
            )
        )

    def create_events(self, year):
        """Create fake events for the boost year if none exist for it."""
        if Event.objects.filter(date__year=year).exists():
            return 0
        today = date.today()
        latest_possible = min(today, date(year, 12, 31))
        if latest_possible.year != year:
            return 0
        span = (latest_possible - date(year, 1, 1)).days
        num_created = 0
        for index, (race_name, shortname, km) in enumerate(RACE_NAMES):
            race, _ = Race.objects.get_or_create(
                name=race_name,
                defaults={"shortname": shortname, "slug": shortname.lower()},
            )
            distance, _ = Distance.objects.get_or_create(
                name=f"{int(km)} Km", defaults={"slug": f"{int(km)}km", "km": km}
            )
            offset = int(span * (index + 1) / len(RACE_NAMES))
            event_date = date(year, 1, 1) + timedelta(days=offset)
            if event_date > today:
                continue
            Event.objects.get_or_create(
                race=race,
                distance=distance,
                date=event_date,
                defaults={"city": "Waterloo"},
            )
            num_created += 1
        return num_created


def load_fake_config(path):
    with open(path) as f:
        return json.load(f)
